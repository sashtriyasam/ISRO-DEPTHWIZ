"""Desktop bridge backend selection: real DA-V2 opt-in, loud failure otherwise.

Covers the ``scripts/backend_bridge.py`` and ``scripts/depthwiz_service.py``
selection boundary without touching model semantics:

* unknown backends fail loudly (no synthetic substitution),
* missing checkpoints fail loudly,
* the service registry degrades factually to synthetic-only,
* the real DA-V2 terrain path (gated) emits the canonical stages with a
  relative depth section and a metric DSM/mesh.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.ingestion.fixtures import make_png

BRIDGE = Path("scripts/backend_bridge.py")
SERVICE = Path("scripts/depthwiz_service.py")


def run_bridge(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Invoke the bridge script with the current interpreter."""
    merged = dict(os.environ)
    # pytest's pythonpath ini option does not propagate to subprocesses.
    merged.setdefault("PYTHONPATH", "src")
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(BRIDGE), *args],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        env=merged,
        timeout=300,
    )


def test_unknown_backend_fails_loudly() -> None:
    """An unknown backend is an error, never a silent synthetic run."""
    proc = run_bridge("--backend", "bogus-backend", "--terrain", "4", "4")
    assert proc.returncode != 0
    payload = json.loads(proc.stdout)
    assert "unknown backend" in payload["error"]
    assert "synthetic" not in payload["error"].lower() or "supported" in payload["error"].lower()


def test_missing_checkpoint_fails_loudly(tmp_path: Path) -> None:
    """Real backend without a checkpoint fails instead of substituting."""
    make_png(tmp_path / "a.png")
    proc = run_bridge(
        "--backend",
        "depth-anything-v2-small",
        "--terrain-file",
        str(tmp_path / "a.png"),
        env={"DW_DAV2_CKPT": str(tmp_path / "missing.pth")},
    )
    assert proc.returncode != 0
    payload = json.loads(proc.stdout)
    assert "error" in payload
    # The failure must identify the real backend problem, never silently
    # succeed with a synthetic artifact.
    assert "synthetic-depth" not in json.dumps(payload.get("depth_result", {}))


def test_service_registry_degrades_without_checkpoint() -> None:
    """Capabilities stay factual when DA-V2 assets are absent."""
    code = (
        "import sys; sys.path.insert(0, 'scripts');"
        "from depthwiz_service import build_backends;"
        "print(sorted(build_backends()))"
    )
    merged = dict(os.environ, DW_DAV2_CKPT="definitely/missing.pth")
    # Hide the upstream runtime if it happens to be on PYTHONPATH.
    merged["PYTHONPATH"] = "src"
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        env=merged,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "['synthetic-depth']"


_REAL_CKPT = os.environ.get("DW_DAV2_CKPT", "")
_REAL_ENABLED = os.environ.get("DW_DAV2_REAL_SMOKE", "0") == "1"
_SKIP = "Real bridge smoke skipped: set DW_DAV2_REAL_SMOKE=1 and DW_DAV2_CKPT=<path>"


@pytest.mark.skipif(not _REAL_ENABLED or not _REAL_CKPT, reason=_SKIP)
def test_real_dav2_terrain_payload(tmp_path: Path) -> None:
    """Gated: real DA-V2 through the desktop bridge entry point."""
    make_png(tmp_path / "a.png")
    proc = run_bridge(
        "--backend",
        "depth-anything-v2-small",
        "--terrain-file",
        str(tmp_path / "a.png"),
    )
    assert proc.returncode == 0, proc.stdout[-2000:]
    payload = json.loads(proc.stdout)
    assert payload["depth_result"]["model_name"] == "depth-anything-v2-small"
    assert payload["depth_result"]["depth_scale"] == "relative"
    assert payload["depth_result"]["units"] is None
    assert payload["dsm"]["units"] == "meters"
    assert payload["mesh"]["vertex_count"] > 0
    assert payload["stages"] == [
        "preprocessing",
        "inference_running",
        "calibrating",
        "dsm_generation",
        "mesh_generation",
    ]
