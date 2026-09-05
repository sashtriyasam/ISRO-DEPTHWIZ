"""Provisioning workflow tests (deterministic; no downloads).

Unit tests use temporary directories and a locally created git repo.
Nothing here fetches the 100 MB checkpoint or installs packages, except
the explicitly gated end-to-end smoke at the bottom.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import depthwizard.runtime.provision  # noqa: F401  (ensures sys.modules entry)
from depthwizard.runtime.provision import (
    CORE_MODE,
    DAV2_MODE,
    ProvisionRequest,
    normalize_git_url,
    provision,
    venv_interpreter,
)

prov_mod = sys.modules["depthwizard.runtime.provision"]


def _git_available() -> bool:
    try:
        proc = subprocess.run(["git", "--version"], capture_output=True, timeout=30)
    except Exception:
        return False
    return proc.returncode == 0


def _make_repo(path: Path, remote_url: str) -> str:
    """Create a single-commit git repo; return its HEAD SHA."""
    path.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1")
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, env=env)
    subprocess.run(
        ["git", "config", "user.email", "provision-test@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
        env=env,
    )
    subprocess.run(
        ["git", "config", "user.name", "provision-test"],
        cwd=path,
        check=True,
        capture_output=True,
        env=env,
    )
    (path / "dpt.py").write_text("# fixture\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True, env=env)
    subprocess.run(
        ["git", "commit", "-m", "fixture"], cwd=path, check=True, capture_output=True, env=env
    )
    subprocess.run(
        ["git", "remote", "add", "origin", remote_url],
        cwd=path,
        check=True,
        capture_output=True,
        env=env,
    )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, check=True, capture_output=True, text=True, env=env
    )
    return head.stdout.strip()


# ---------------------------------------------------------------------------
# Layout + version + pip command construction (pure)
# ---------------------------------------------------------------------------


def test_venv_layout_windows() -> None:
    """Windows runtimes expose Scripts/python.exe (pure path logic)."""
    assert venv_interpreter(Path("R:/rt"), platform="win32") == Path("R:/rt/Scripts/python.exe")


def test_venv_layout_posix() -> None:
    """POSIX runtimes expose bin/python (pure path logic)."""
    assert venv_interpreter(Path("/opt/rt"), platform="linux") == Path("/opt/rt/bin/python")


def test_python_version_accepted() -> None:
    """Supported interpreters pass the version gate."""
    status = prov_mod.check_python_version((3, 12, 10))
    assert status.ok
    assert status.code == "OK"


def test_python_version_rejected() -> None:
    """Old interpreters fail with the taxonomy code (no substitution)."""
    status = prov_mod.check_python_version((3, 10, 0))
    assert not status.ok
    assert status.code == "PYTHON_VERSION_UNSUPPORTED"


def test_pip_uses_project_metadata() -> None:
    """Install argv references the project root + extra (no dep duplication)."""
    interp = Path("/rt/python")
    root = Path("/repo")
    core = prov_mod.pip_install_args(interp, root, CORE_MODE)
    dav2 = prov_mod.pip_install_args(interp, root, DAV2_MODE)
    assert core == [str(interp), "-m", "pip", "install", "-e", str(root)]
    assert dav2 == [str(interp), "-m", "pip", "install", "-e", f"{root}[dav2]"]
    assert not any("torch" in arg for arg in dav2)


def test_unknown_mode_rejected(tmp_path: Path) -> None:
    """Unknown modes fail structurally before touching the machine."""
    status = provision(ProvisionRequest(runtime_dir=tmp_path / "rt", mode="gpu"))
    assert status.ready is False
    assert status.steps[0].code == "PROVISION_UNKNOWN_MODE"


def test_file_as_runtime_dir_rejected(tmp_path: Path) -> None:
    """A file where the runtime should live is a structured failure."""
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    status = provision(ProvisionRequest(runtime_dir=blocker, mode=CORE_MODE, skip_pip=True))
    assert status.ready is False
    assert status.steps[0].code == "PROVISION_INVALID_RUNTIME_DIR"


# ---------------------------------------------------------------------------
# Upstream identity (local git fixture; fixed-identity comparison)
# ---------------------------------------------------------------------------


def test_git_url_normalization() -> None:
    """SSH/HTTPS/.git spellings compare as one identity (pure)."""
    https = "https://github.com/DepthAnything/Depth-Anything-V2"
    assert normalize_git_url(
        "git@github.com:DepthAnything/Depth-Anything-V2.git"
    ) == normalize_git_url(https)
    assert normalize_git_url(https + ".git") == normalize_git_url(https)
    assert normalize_git_url("https://github.com/other/repo") != normalize_git_url(https)


@pytest.mark.skipif(not _git_available(), reason="git binary unavailable")
def test_source_accepts_matching_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A repo with the (monkeypatched) fixed identity + HEAD verifies."""
    repo = tmp_path / "upstream"
    head = _make_repo(repo, "https://example.com/fixed-upstream.git")
    monkeypatch.setattr(prov_mod, "FIXED_UPSTREAM_URL", "https://example.com/fixed-upstream.git")
    monkeypatch.setattr(prov_mod, "FIXED_UPSTREAM_REVISION", head)
    status = prov_mod.verify_source_dir(repo)
    assert status.ok
    assert status.code == "OK"


@pytest.mark.skipif(not _git_available(), reason="git binary unavailable")
def test_source_rejects_wrong_revision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Right repository, wrong HEAD: loud mismatch, never silent."""
    repo = tmp_path / "upstream"
    _make_repo(repo, "https://example.com/fixed-upstream.git")
    monkeypatch.setattr(prov_mod, "FIXED_UPSTREAM_URL", "https://example.com/fixed-upstream.git")
    monkeypatch.setattr(prov_mod, "FIXED_UPSTREAM_REVISION", "0" * 40)
    status = prov_mod.verify_source_dir(repo)
    assert not status.ok
    assert status.code == "UPSTREAM_REVISION_MISMATCH"


@pytest.mark.skipif(not _git_available(), reason="git binary unavailable")
def test_source_rejects_wrong_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Wrong remote: identity mismatch even with a valid git repo."""
    repo = tmp_path / "upstream"
    head = _make_repo(repo, "https://example.com/other.git")
    monkeypatch.setattr(prov_mod, "FIXED_UPSTREAM_URL", "https://example.com/fixed-upstream.git")
    monkeypatch.setattr(prov_mod, "FIXED_UPSTREAM_REVISION", head)
    status = prov_mod.verify_source_dir(repo)
    assert not status.ok
    assert status.code == "UPSTREAM_REPOSITORY_MISMATCH"


def test_source_missing_reports_absent(tmp_path: Path) -> None:
    """Absent source is reported, not fabricated."""
    status = prov_mod.verify_source_dir(tmp_path / "nope")
    assert not status.ok
    assert status.code == "UPSTREAM_SOURCE_MISSING"


# ---------------------------------------------------------------------------
# Checkpoint handling + idempotence (local bytes only)
# ---------------------------------------------------------------------------


def test_checkpoint_stored_from_verified_src(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hash-verified source file is stored into the data dir."""
    import hashlib

    payload = b"provision-checkpoint-fixture"
    src = tmp_path / "src.pth"
    src.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    monkeypatch.setattr(prov_mod, "CHECKPOINT_SHA256", digest)
    data = tmp_path / "data"
    status = prov_mod.ensure_checkpoint(data, src=src)
    assert status.ok
    assert (data / "checkpoints" / "depth_anything_v2_vits.pth").read_bytes() == payload


def test_checkpoint_mismatch_rejected(tmp_path: Path) -> None:
    """A tampered source never reaches the data dir."""
    src = tmp_path / "bad.pth"
    src.write_bytes(b"tampered")
    data = tmp_path / "data"
    status = prov_mod.ensure_checkpoint(data, src=src)
    assert not status.ok
    assert status.code == "CHECKPOINT_HASH_MISMATCH"
    assert not (data / "checkpoints" / "depth_anything_v2_vits.pth").exists()


def test_valid_checkpoint_never_replaced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Idempotence: a valid stored checkpoint survives re-provisioning."""
    import hashlib

    payload = b"stable-checkpoint"
    monkeypatch.setattr(prov_mod, "CHECKPOINT_SHA256", hashlib.sha256(payload).hexdigest())
    data = tmp_path / "data"
    dest_dir = data / "checkpoints"
    dest_dir.mkdir(parents=True)
    dest = dest_dir / "depth_anything_v2_vits.pth"
    dest.write_bytes(payload)
    before = (dest.stat().st_mtime_ns, dest.read_bytes())
    status = prov_mod.ensure_checkpoint(data, src=tmp_path / "other.pth")
    assert status.ok
    assert status.reused is True
    assert (dest.stat().st_mtime_ns, dest.read_bytes()) == before


# ---------------------------------------------------------------------------
# Status mapping: no synthetic fallback, offline fields
# ---------------------------------------------------------------------------


def test_dav2_mode_without_assets_is_not_ready(tmp_path: Path) -> None:
    """Missing assets yield dav2_ready False (never synthetic success)."""
    request = ProvisionRequest(
        runtime_dir=tmp_path / "rt",
        mode=DAV2_MODE,
        skip_pip=True,
        data_dir=tmp_path / "empty-data",
    )
    status = provision(request)
    assert status.ready is False
    assert status.core_ready is True
    assert status.dav2_ready is False
    codes = [step.code for step in status.steps]
    assert "UPSTREAM_SOURCE_MISSING" in codes or "CHECKPOINT_MISSING" in codes


def test_status_serializes_without_absolute_paths(tmp_path: Path) -> None:
    """Host status carries labels, not machine paths."""
    status = provision(ProvisionRequest(runtime_dir=tmp_path / "rt", mode=CORE_MODE, skip_pip=True))
    document = status.to_dict()
    assert document["ready"] is True
    assert document["offline_ready"] is True
    assert document["service_launch_ready"] is True
    assert str(tmp_path) not in json.dumps(document)


# ---------------------------------------------------------------------------
# CLI contract (fast paths only; no downloads)
# ---------------------------------------------------------------------------


def test_cli_core_provision(tmp_path: Path) -> None:
    """CLI provisions a core runtime venv and reports JSON."""
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/provision_runtime.py",
            "--runtime-dir",
            str(tmp_path / "rt"),
            "--mode",
            "core",
            "--skip-pip",
        ],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr
    document = json.loads(proc.stdout)
    assert document["ready"] is True
    assert document["mode"] == "core"
    assert str(tmp_path) not in proc.stdout


def test_cli_unknown_mode_is_misuse(tmp_path: Path) -> None:
    """CLI misuse exits 2 (argparse), not a provisioning failure."""
    proc = subprocess.run(
        [
            sys.executable,
            "scripts/provision_runtime.py",
            "--runtime-dir",
            str(tmp_path / "rt"),
            "--mode",
            "gpu",
        ],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        timeout=120,
    )
    assert proc.returncode == 2


def test_cli_idempotent_rerun(tmp_path: Path) -> None:
    """Second run reuses the venv and reports the same verified state."""
    argv = [
        sys.executable,
        "scripts/provision_runtime.py",
        "--runtime-dir",
        str(tmp_path / "rt"),
        "--mode",
        "core",
        "--skip-pip",
    ]
    first = subprocess.run(argv, capture_output=True, text=True, cwd=Path.cwd(), timeout=300)
    second = subprocess.run(argv, capture_output=True, text=True, cwd=Path.cwd(), timeout=300)
    assert first.returncode == 0 and second.returncode == 0
    rerun = json.loads(second.stdout)
    venv_steps = [step for step in rerun["steps"] if step["name"] == "venv"]
    assert venv_steps and venv_steps[0]["reused"] is True
    assert rerun["ready"] is True


# ---------------------------------------------------------------------------
# Gated end-to-end: real pip install + runtime check + service readiness
# ---------------------------------------------------------------------------

_PROVISION_SMOKE = os.environ.get("DW_PROVISION_SMOKE", "0") == "1"
_SMOKE_SKIP = "Provisioning smoke skipped: set DW_PROVISION_SMOKE=1 to enable"


@pytest.mark.skipif(not _PROVISION_SMOKE, reason=_SMOKE_SKIP)
def test_provisioned_core_runtime_runs_service(tmp_path: Path) -> None:
    """Gated: real core install, runtime_check, and service capabilities."""
    runtime = tmp_path / "rt"
    argv = [
        sys.executable,
        "scripts/provision_runtime.py",
        "--runtime-dir",
        str(runtime),
        "--mode",
        "core",
        "--pretty",
    ]
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=Path.cwd(), timeout=900)
    assert proc.returncode == 0, proc.stderr[-2000:]
    document = json.loads(proc.stdout)
    assert document["ready"] is True

    if sys.platform == "win32":
        interpreter = runtime / "Scripts" / "python.exe"
    else:
        interpreter = runtime / "bin" / "python"
    assert interpreter.is_file()

    check = subprocess.run(
        [str(interpreter), "scripts/runtime_check.py"],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        timeout=300,
    )
    assert check.returncode == 0, check.stderr
    assert json.loads(check.stdout)["healthy"] is True

    service = subprocess.run(
        [str(interpreter), "scripts/depthwiz_service.py"],
        input='{"capabilities": true}',
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        timeout=300,
    )
    assert service.returncode == 0, service.stderr
    capabilities = json.loads(service.stdout)["capabilities"]
    assert capabilities["available_backends"] == ["synthetic-depth"]
