"""Packaging diagnostics: environment facts for setup and runtime checks.

All availability probes use import *discovery* (``find_spec``) so the
check itself never loads torch or the model. Checkpoint verification
is a local file hash. Nothing here downloads, installs, or phones
home. Paths reported to callers use location labels
(``explicit``/``env``/``data-dir``/``repo-dev``/``cwd``), never raw
absolute paths, so records stay machine-portable.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from depthwizard.backends.depth_anything_v2 import (
    CHECKPOINT_FILE as CHECKPOINT_FILE,
)
from depthwizard.backends.depth_anything_v2 import (
    CHECKPOINT_SHA256 as CHECKPOINT_SHA256,
)
from depthwizard.backends.depth_anything_v2 import (
    UPSTREAM_REVISION as UPSTREAM_REVISION,
)
from depthwizard.backends.depth_anything_v2 import (
    UPSTREAM_URL as UPSTREAM_URL,
)
from depthwizard.version import __version__

#: Minimum interpreter (mirrors ``pyproject.toml`` ``requires-python``).
MIN_PYTHON = (3, 11)

#: Core runtime import names (always required).
CORE_MODULES = ("pydantic", "PIL", "rasterio", "numpy")

#: Optional ML runtime import names (DA-V2 inference only).
DAV2_MODULES = ("torch", "torchvision", "cv2")

#: Upstream DA-V2 source package name (pinned clone on PYTHONPATH).
DAV2_SOURCE = "depth_anything_v2"

#: Host-managed data directory override (packaged installations).
DATA_ENV = "DEPTHWIZARD_DATA"

#: Host-resolved absolute checkpoint override (packaged installations).
CHECKPOINT_ENV = "DW_DAV2_CKPT"

#: Packaged checkpoint layout relative to the data directory.
DATA_CHECKPOINT_REL = Path("checkpoints") / CHECKPOINT_FILE


@dataclass(frozen=True)
class CheckStatus:
    """One named check outcome (JSON-safe via ``asdict``-style mapping)."""

    name: str
    ok: bool
    code: str
    detail: str
    extra: dict[str, str] = field(default_factory=dict)


def default_data_dir() -> Path:
    """Host-managed data directory (override with ``DEPTHWIZARD_DATA``)."""
    override = os.environ.get(DATA_ENV)
    if override:
        return Path(override)
    home = Path.home()
    if sys.platform == "win32":
        base = os.environ.get("APPDATA")
        return Path(base) / "DepthWizard" if base else home / "DepthWizard"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "DepthWizard"
    xdg = os.environ.get("XDG_DATA_HOME")
    return Path(xdg) / "depthwizard" if xdg else home / ".local" / "share" / "depthwizard"


def _repo_dev_checkpoint() -> Path | None:
    """Developer-checkout checkpoint (source tree layout, if present)."""
    try:
        root = Path(__file__).resolve().parents[3]
        if (root / "src").exists():
            return root / "checkpoints" / CHECKPOINT_FILE
    except Exception:
        pass
    return None


def resolve_checkpoint(explicit: str | Path | None = None) -> tuple[Path | None, str]:
    """Locate the DA-V2 checkpoint file without importing torch.

    Order: explicit argument → ``DW_DAV2_CKPT`` → packaged data dir →
    repo-dev ``checkpoints/`` → ``cwd/checkpoints/``. Returns the first
    existing file (or ``None``) plus a location label describing where
    it came from (``explicit``/``env``/``data-dir``/``repo-dev``/``cwd``
    /``absent``).
    """
    if explicit is not None:
        candidate = Path(explicit)
        return (candidate, "explicit") if candidate.is_file() else (None, "absent")
    env = os.environ.get(CHECKPOINT_ENV)
    if env:
        candidate = Path(env)
        return (candidate, "env") if candidate.is_file() else (None, "absent")
    data_candidate = default_data_dir() / DATA_CHECKPOINT_REL
    if data_candidate.is_file():
        return data_candidate, "data-dir"
    repo_candidate = _repo_dev_checkpoint()
    if repo_candidate is not None and repo_candidate.is_file():
        return repo_candidate, "repo-dev"
    cwd_candidate = Path.cwd() / "checkpoints" / CHECKPOINT_FILE
    if cwd_candidate.is_file():
        return cwd_candidate, "cwd"
    return None, "absent"


def sha256_file(path: Path) -> str:
    """Stream a file's SHA-256 hex digest."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checkpoint(path: Path, expected: str = CHECKPOINT_SHA256) -> CheckStatus:
    """Accept a checkpoint only when its file hash matches exactly."""
    if not path.is_file():
        return CheckStatus(
            name="checkpoint",
            ok=False,
            code="CHECKPOINT_MISSING",
            detail=f"checkpoint not found: {path.name}",
        )
    actual = sha256_file(path)
    if actual != expected:
        return CheckStatus(
            name="checkpoint",
            ok=False,
            code="CHECKPOINT_HASH_MISMATCH",
            detail=f"hash mismatch for {path.name}",
            extra={"actual": actual, "expected": expected},
        )
    return CheckStatus(
        name="checkpoint",
        ok=True,
        code="OK",
        detail=f"verified {path.name}",
        extra={"sha256": actual},
    )


def module_available(name: str) -> bool:
    """Whether a module is import-discoverable (never imports it)."""
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def upstream_revision() -> str | None:
    """Pinned-clone git revision, when the source tree exposes git."""
    try:
        spec = importlib.util.find_spec(DAV2_SOURCE)
    except Exception:
        return None
    if spec is None:
        return None
    locations = list(getattr(spec, "submodule_search_locations", []) or [])
    if spec.origin not in (None, "namespace"):
        locations.append(str(Path(spec.origin).parent))
    for location in locations:
        try:
            proc = subprocess.run(
                ["git", "-C", location, "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception:
            continue
        revision = proc.stdout.strip()
        if proc.returncode == 0 and revision:
            return revision
    return None


def availability_report() -> dict[str, object]:
    """Machine-readable availability snapshot (no heavy imports)."""
    core = {name: module_available(name) for name in CORE_MODULES}
    dav2 = {name: module_available(name) for name in DAV2_MODULES}
    source = module_available(DAV2_SOURCE)
    checkpoint, location = resolve_checkpoint()
    checkpoint_status = verify_checkpoint(checkpoint) if checkpoint is not None else None
    revision = upstream_revision()
    try:
        from depthwizard.backends.synthetic import SyntheticDepthBackend  # noqa: F401

        backend_importable = True
    except Exception:
        backend_importable = False
    try:
        from depthwizard.service import LocalService  # noqa: F401

        service_importable = True
    except Exception:
        service_importable = False
    return {
        "python": {
            "version": ".".join(str(part) for part in sys.version_info[:3]),
            "meets_minimum": (sys.version_info.major, sys.version_info.minor) >= MIN_PYTHON,
        },
        "engine_version": __version__,
        "core_modules": core,
        "core_ready": all(core.values()) and backend_importable and service_importable,
        "dav2_modules": dav2,
        "dav2_source_present": source,
        "dav2_source_revision": revision,
        "dav2_revision_matches_pin": (revision == UPSTREAM_REVISION) if revision else False,
        "dav2_ready": all(dav2.values()) and source,
        "checkpoint": {
            "location": location,
            "present": checkpoint is not None,
            "sha_match": bool(checkpoint_status and checkpoint_status.ok),
            "code": checkpoint_status.code if checkpoint_status else "CHECKPOINT_MISSING",
            "expected_sha256": CHECKPOINT_SHA256,
        },
        "provenance": {
            "checkpoint_file": CHECKPOINT_FILE,
            "upstream_url": UPSTREAM_URL,
            "upstream_revision_pin": UPSTREAM_REVISION,
        },
    }
