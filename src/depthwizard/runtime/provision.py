"""Managed-runtime provisioning (setup automation, never science).

Establishes an isolated virtual environment, installs the project from
its own packaging metadata (``pyproject.toml`` stays the single source
of truth — no duplicated dependency lists), provisions the pinned
DA-V2 upstream source and the SHA-verified checkpoint, then reports a
host-consumable JSON status (``provision`` → ``verify`` → launch
readiness) without requiring the host to understand Python internals.

Network policy: provisioning steps (pip, git clone, checkpoint fetch)
may use the network. Runtime inference after provisioning must not.
Fixed identities only — no arbitrary URLs, packages, or modules.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from depthwizard.runtime.diagnostics import (
    CHECKPOINT_FILE,
    CHECKPOINT_SHA256,
    MIN_PYTHON,
    UPSTREAM_REVISION,
    UPSTREAM_URL,
    default_data_dir,
    sha256_file,
)

#: Fixed upstream git identity (never user-supplied).
FIXED_UPSTREAM_URL = UPSTREAM_URL
FIXED_UPSTREAM_REVISION = UPSTREAM_REVISION

#: Fixed checkpoint download identity (fetch mode only, never default).
FIXED_CHECKPOINT_URL = (
    "https://huggingface.co/depth-anything/Depth-Anything-V2-Small"
    "/resolve/main/depth_anything_v2_vits.pth"
)
FIXED_CHECKPOINT_SHA256 = CHECKPOINT_SHA256

#: Upstream source layout inside a data directory.
SOURCE_DIR_NAME = "dav2-upstream"

#: Provisioning modes.
CORE_MODE = "core"
DAV2_MODE = "dav2"

#: Network timeouts (seconds) for provisioning steps only.
_CLONE_TIMEOUT = 600
_FETCH_TIMEOUT = 900
_SUBPROCESS_TIMEOUT = 600


@dataclass(frozen=True)
class StepStatus:
    """One provisioning step outcome (JSON-safe)."""

    name: str
    ok: bool
    code: str
    detail: str
    reused: bool = False


@dataclass
class ProvisionRequest:
    """Host-facing provisioning parameters (all paths host-chosen)."""

    runtime_dir: Path
    mode: str = CORE_MODE
    python: Path | None = None
    project_root: Path | None = None
    data_dir: Path | None = None
    checkpoint_src: Path | None = None
    fetch_checkpoint: bool = False
    skip_pip: bool = False


def check_python_version(version: tuple[int, ...]) -> StepStatus:
    """Accept interpreters meeting the runtime minimum (pure)."""
    ok = (version[0], version[1]) >= MIN_PYTHON if len(version) >= 2 else False
    return StepStatus(
        name="python",
        ok=ok,
        code="OK" if ok else "PYTHON_VERSION_UNSUPPORTED",
        detail=f"python {'.'.join(str(part) for part in version[:3])}",
    )


def probe_python(interpreter: Path) -> tuple[tuple[int, ...], StepStatus]:
    """Report a base interpreter's version (argv only, no shell)."""
    try:
        proc = subprocess.run(
            [
                str(interpreter),
                "-c",
                "import json,sys;print(json.dumps(list(sys.version_info[:3])))",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        status = StepStatus(
            name="python", ok=False, code="PYTHON_NOT_FOUND", detail=str(interpreter)
        )
        return (0,), status
    except Exception as exc:
        status = StepStatus(name="python", ok=False, code="PYTHON_PROBE_FAILED", detail=str(exc))
        return (0,), status
    if proc.returncode != 0:
        return (0,), StepStatus(
            name="python",
            ok=False,
            code="PYTHON_PROBE_FAILED",
            detail=proc.stderr.strip()[-500:],
        )
    try:
        version = tuple(int(part) for part in json.loads(proc.stdout))
    except Exception:
        return (0,), StepStatus(
            name="python", ok=False, code="PYTHON_PROBE_FAILED", detail="unparseable version"
        )
    return version, check_python_version(version)


def venv_interpreter(runtime_dir: Path, platform: str = sys.platform) -> Path:
    """Interpreter path for a managed runtime layout (pure)."""
    if platform == "win32":
        return runtime_dir / "Scripts" / "python.exe"
    return runtime_dir / "bin" / "python"


def ensure_runtime_dir(runtime_dir: Path) -> StepStatus:
    """Validate the runtime directory slot (never deletes user data)."""
    if runtime_dir.is_file():
        return StepStatus(
            name="runtime-dir",
            ok=False,
            code="PROVISION_INVALID_RUNTIME_DIR",
            detail=f"not a directory: {runtime_dir.name}",
        )
    try:
        runtime_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        return StepStatus(
            name="runtime-dir",
            ok=False,
            code="PROVISION_PERMISSION_DENIED",
            detail=str(exc),
        )
    except OSError as exc:
        return StepStatus(
            name="runtime-dir", ok=False, code="PROVISION_RUNTIME_DIR_FAILED", detail=str(exc)
        )
    return StepStatus(name="runtime-dir", ok=True, code="OK", detail="runtime directory ready")


def ensure_venv(runtime_dir: Path, base_python: Path) -> tuple[Path, StepStatus]:
    """Create (or reuse) the isolated managed environment."""
    interpreter = venv_interpreter(runtime_dir)
    if interpreter.is_file():
        version, status = probe_python(interpreter)
        if status.ok:
            return interpreter, StepStatus(
                name="venv",
                ok=True,
                code="OK",
                detail=f"reused ({status.detail})",
                reused=True,
            )
        return interpreter, StepStatus(
            name="venv",
            ok=False,
            code="PROVISION_RUNTIME_DIR_CONFLICT",
            detail=f"existing environment unusable ({status.code}); remove it explicitly",
        )
    try:
        proc = subprocess.run(
            [str(base_python), "-m", "venv", str(runtime_dir)],
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
    except Exception as exc:
        return interpreter, StepStatus(
            name="venv", ok=False, code="VENV_CREATION_FAILED", detail=str(exc)
        )
    if proc.returncode != 0 or not interpreter.is_file():
        return interpreter, StepStatus(
            name="venv",
            ok=False,
            code="VENV_CREATION_FAILED",
            detail=proc.stderr.strip()[-500:],
        )
    return interpreter, StepStatus(name="venv", ok=True, code="OK", detail="created")


def pip_install_args(interpreter: Path, project_root: Path, mode: str) -> list[str]:
    """Pip argv from project metadata (pure; dependency lists live in pyproject)."""
    target = str(project_root) + ("[dav2]" if mode == DAV2_MODE else "")
    return [str(interpreter), "-m", "pip", "install", "-e", target]


def run_pip_install(interpreter: Path, project_root: Path, mode: str) -> StepStatus:
    """Install the project into the managed environment."""
    try:
        proc = subprocess.run(
            pip_install_args(interpreter, project_root, mode),
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT,
        )
    except Exception as exc:
        return StepStatus(name="pip-install", ok=False, code="PIP_INSTALL_FAILED", detail=str(exc))
    if proc.returncode != 0:
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-5:]
        return StepStatus(
            name="pip-install",
            ok=False,
            code="PIP_INSTALL_FAILED",
            detail=" | ".join(tail)[-500:],
        )
    return StepStatus(name="pip-install", ok=True, code="OK", detail=f"installed ({mode})")


def normalize_git_url(url: str) -> str:
    """Canonicalize a GitHub remote URL for identity comparison (pure)."""
    normalized = url.strip().lower()
    if normalized.startswith("git@github.com:"):
        normalized = "https://github.com/" + normalized[len("git@github.com:") :]
    if normalized.endswith(".git"):
        normalized = normalized[: -len(".git")]
    return normalized.rstrip("/")


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git argv (list only, never shell)."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=120,
    )


def verify_source_dir(
    path: Path, url: str | None = None, revision: str | None = None
) -> StepStatus:
    """Verify a provisioned upstream checkout (identity + pinned HEAD)."""
    expected_url = FIXED_UPSTREAM_URL if url is None else url
    expected_revision = FIXED_UPSTREAM_REVISION if revision is None else revision
    if not path.exists():
        return StepStatus(
            name="dav2-source", ok=False, code="UPSTREAM_SOURCE_MISSING", detail=path.name
        )
    if not (path / ".git").exists():
        return StepStatus(
            name="dav2-source", ok=False, code="UPSTREAM_NOT_A_REPO", detail=path.name
        )
    try:
        remote = _git(["config", "--get", "remote.origin.url"], path)
        head = _git(["rev-parse", "HEAD"], path)
    except FileNotFoundError:
        return StepStatus(
            name="dav2-source", ok=False, code="UPSTREAM_GIT_UNAVAILABLE", detail="git not found"
        )
    except Exception as exc:
        return StepStatus(
            name="dav2-source", ok=False, code="UPSTREAM_GIT_UNAVAILABLE", detail=str(exc)
        )
    if remote.returncode != 0 or normalize_git_url(remote.stdout.strip()) != normalize_git_url(
        expected_url
    ):
        return StepStatus(
            name="dav2-source",
            ok=False,
            code="UPSTREAM_REPOSITORY_MISMATCH",
            detail="remote origin is not the fixed upstream identity",
        )
    if head.returncode != 0 or head.stdout.strip() != expected_revision:
        return StepStatus(
            name="dav2-source",
            ok=False,
            code="UPSTREAM_REVISION_MISMATCH",
            detail="HEAD is not the pinned revision",
        )
    return StepStatus(
        name="dav2-source",
        ok=True,
        code="OK",
        detail=f"verified {expected_revision[:12]}",
        reused=True,
    )


def ensure_source(dest: Path) -> StepStatus:
    """Clone + pin the fixed upstream source (or reuse a verified one)."""
    existing = verify_source_dir(dest)
    if existing.ok:
        return existing
    if dest.exists():
        # Present but wrong: never silently replace user data.
        return existing
    try:
        clone = subprocess.run(
            ["git", "clone", FIXED_UPSTREAM_URL, str(dest)],
            capture_output=True,
            text=True,
            timeout=_CLONE_TIMEOUT,
        )
    except FileNotFoundError:
        return StepStatus(
            name="dav2-source", ok=False, code="UPSTREAM_GIT_UNAVAILABLE", detail="git not found"
        )
    except Exception as exc:
        return StepStatus(
            name="dav2-source", ok=False, code="UPSTREAM_CLONE_FAILED", detail=str(exc)
        )
    if clone.returncode != 0:
        return StepStatus(
            name="dav2-source",
            ok=False,
            code="UPSTREAM_CLONE_FAILED",
            detail=clone.stderr.strip()[-500:],
        )
    checkout = _git(["checkout", FIXED_UPSTREAM_REVISION], dest)
    if checkout.returncode != 0:
        return StepStatus(
            name="dav2-source",
            ok=False,
            code="UPSTREAM_REVISION_MISMATCH",
            detail="pinned revision unavailable after clone",
        )
    return verify_source_dir(dest)


def ensure_checkpoint(
    data_dir: Path,
    src: Path | None = None,
    fetch: bool = False,
) -> StepStatus:
    """Provide a verified checkpoint (keep valid ones; never trust blindly)."""
    dest_dir = data_dir / "checkpoints"
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return StepStatus(
            name="checkpoint", ok=False, code="PROVISION_PERMISSION_DENIED", detail=str(exc)
        )
    dest = dest_dir / CHECKPOINT_FILE
    if dest.is_file():
        try:
            if sha256_file(dest) == CHECKPOINT_SHA256:
                return StepStatus(
                    name="checkpoint", ok=True, code="OK", detail="kept verified", reused=True
                )
        except OSError:
            pass
        # Present but invalid: stage aside, never silently trust or delete.
        try:
            dest.rename(dest.with_suffix(".invalid"))
        except OSError as exc:
            return StepStatus(
                name="checkpoint",
                ok=False,
                code="CHECKPOINT_HASH_MISMATCH",
                detail=f"invalid checkpoint quarantined-failed: {exc}",
            )
        return StepStatus(
            name="checkpoint",
            ok=False,
            code="CHECKPOINT_HASH_MISMATCH",
            detail="invalid checkpoint quarantined; re-provision required",
        )
    if src is not None:
        if not src.is_file():
            return StepStatus(
                name="checkpoint", ok=False, code="CHECKPOINT_MISSING", detail=str(src.name)
            )
        try:
            if sha256_file(src) != CHECKPOINT_SHA256:
                return StepStatus(
                    name="checkpoint",
                    ok=False,
                    code="CHECKPOINT_HASH_MISMATCH",
                    detail="source checkpoint hash mismatch; rejected",
                )
            shutil.copyfile(src, dest)
        except OSError as exc:
            return StepStatus(
                name="checkpoint", ok=False, code="PROVISION_PERMISSION_DENIED", detail=str(exc)
            )
        return StepStatus(name="checkpoint", ok=True, code="OK", detail="verified and stored")
    if fetch:
        return _fetch_checkpoint(dest)
    return StepStatus(
        name="checkpoint",
        ok=False,
        code="CHECKPOINT_MISSING",
        detail="no source provided (use --checkpoint-src or --fetch-checkpoint)",
    )


def _fetch_checkpoint(dest: Path) -> StepStatus:
    """Download ONLY the fixed checkpoint identity, then verify."""
    try:
        request = urllib.request.Request(
            FIXED_CHECKPOINT_URL, headers={"User-Agent": "DepthWizard-provision"}
        )
        with urllib.request.urlopen(request, timeout=_FETCH_TIMEOUT) as response:
            with open(dest, "wb") as handle:
                shutil.copyfileobj(response, handle)
    except Exception as exc:
        if dest.exists():
            dest.unlink(missing_ok=True)
        return StepStatus(
            name="checkpoint", ok=False, code="CHECKPOINT_FETCH_FAILED", detail=str(exc)[-300:]
        )
    try:
        if sha256_file(dest) != CHECKPOINT_SHA256:
            dest.unlink(missing_ok=True)
            return StepStatus(
                name="checkpoint",
                ok=False,
                code="CHECKPOINT_HASH_MISMATCH",
                detail="downloaded bytes failed verification; discarded",
            )
    except OSError as exc:
        return StepStatus(
            name="checkpoint", ok=False, code="PROVISION_PERMISSION_DENIED", detail=str(exc)
        )
    return StepStatus(name="checkpoint", ok=True, code="OK", detail="fetched and verified")


@dataclass
class ProvisionStatus:
    """Host-facing provisioning outcome (JSON-safe via ``to_dict``)."""

    ready: bool
    mode: str
    version: str = "1"
    steps: list[StepStatus] = field(default_factory=list)
    interpreter: str = ""
    data_location: str = ""
    dav2_ready: bool = False
    core_ready: bool = False
    service_launch_ready: bool = False
    offline_ready: bool = False

    def to_dict(self) -> dict[str, object]:
        """Serialize without absolute paths (labels only)."""
        return {
            "version": self.version,
            "ready": self.ready,
            "mode": self.mode,
            "steps": [
                {
                    "name": step.name,
                    "ok": step.ok,
                    "code": step.code,
                    "detail": step.detail,
                    "reused": step.reused,
                }
                for step in self.steps
            ],
            "interpreter": Path(self.interpreter).name if self.interpreter else "",
            "data_location": self.data_location,
            "core_ready": self.core_ready,
            "dav2_ready": self.dav2_ready,
            "service_launch_ready": self.service_launch_ready,
            "offline_ready": self.offline_ready,
        }


def provision(request: ProvisionRequest) -> ProvisionStatus:
    """Run the provisioning workflow (idempotent; no daemon created)."""
    steps: list[StepStatus] = []
    if request.mode not in (CORE_MODE, DAV2_MODE):
        steps.append(
            StepStatus(name="mode", ok=False, code="PROVISION_UNKNOWN_MODE", detail=request.mode)
        )
        return ProvisionStatus(ready=False, mode=request.mode, steps=steps)

    slot = ensure_runtime_dir(request.runtime_dir)
    steps.append(slot)
    if not slot.ok:
        return ProvisionStatus(ready=False, mode=request.mode, steps=steps)

    base_python = request.python or Path(sys.executable)
    _version, python_status = probe_python(base_python)
    steps.append(python_status)
    if not python_status.ok:
        return ProvisionStatus(ready=False, mode=request.mode, steps=steps)

    interpreter, venv_status = ensure_venv(request.runtime_dir, base_python)
    steps.append(venv_status)
    if not venv_status.ok:
        return ProvisionStatus(ready=False, mode=request.mode, steps=steps)

    core_ready = False
    if request.skip_pip:
        steps.append(
            StepStatus(name="pip-install", ok=True, code="SKIPPED", detail="pip step skipped")
        )
        core_ready = True
    else:
        project_root = request.project_root or Path(__file__).resolve().parents[3]
        pip_status = run_pip_install(interpreter, project_root, request.mode)
        steps.append(pip_status)
        core_ready = pip_status.ok
        if not pip_status.ok:
            return ProvisionStatus(
                ready=False,
                mode=request.mode,
                steps=steps,
                interpreter=str(interpreter),
                core_ready=False,
            )

    dav2_ready = False
    data_dir = request.data_dir or default_data_dir()
    if request.mode == DAV2_MODE:
        source_status = ensure_source(data_dir / SOURCE_DIR_NAME)
        steps.append(source_status)
        checkpoint_status = ensure_checkpoint(
            data_dir, src=request.checkpoint_src, fetch=request.fetch_checkpoint
        )
        steps.append(checkpoint_status)
        dav2_ready = source_status.ok and checkpoint_status.ok
        if not dav2_ready:
            return ProvisionStatus(
                ready=False,
                mode=request.mode,
                steps=steps,
                interpreter=str(interpreter),
                data_location="data-dir",
                core_ready=core_ready,
                dav2_ready=False,
            )

    ready = core_ready and (request.mode == CORE_MODE or dav2_ready)
    return ProvisionStatus(
        ready=ready,
        mode=request.mode,
        steps=steps,
        interpreter=str(interpreter),
        data_location="data-dir",
        core_ready=core_ready,
        dav2_ready=dav2_ready,
        service_launch_ready=ready,
        offline_ready=ready,
    )
