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

from tests.ingestion.fixtures import make_geotiff, make_png

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
    merged = dict(
        os.environ,
        DW_DAV2_CKPT="definitely/missing.pth",
        DW_DAV2_SAT_CKPT="definitely/missing_sat.pth",
        DW_NDSM_CKPT="definitely/missing_ndsm.pth",
    )
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
        env={"DW_DEV_CALIBRATION": "1"},
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


def test_large_backend_unknown_fails_loudly() -> None:
    """The large DA-V2 backend fails loudly when unavailable."""
    proc = run_bridge("--backend", "depth-anything-v2-large", "--terrain", "4", "4")
    assert proc.returncode != 0
    payload = json.loads(proc.stdout)
    assert "error" in payload
    assert "unknown backend" in payload["error"] or (
        "depth-anything-v2-large" in payload["error"].lower()
        and "not found" in payload["error"].lower()
    )


def test_mesh_levels_synthetic() -> None:
    """Mesh levels are forwarded to the LOD mesh builder."""
    proc = run_bridge(
        "--backend",
        "synthetic-depth",
        "--terrain",
        "8",
        "8",
        "--mesh-levels",
        "1",
        "4",
    )
    assert proc.returncode == 0, proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["mesh"]["vertex_count"] > 0


def test_calibration_method_huber_synthetic() -> None:
    """Huber calibration method is accepted and reflected in the payload."""
    proc = run_bridge(
        "--backend",
        "synthetic-depth",
        "--terrain",
        "4",
        "4",
        "--calibration-method",
        "scale_offset_huber",
    )
    assert proc.returncode == 0, proc.stdout
    payload = json.loads(proc.stdout)
    assert payload["mesh"]["calibration_method"] == "scale_offset_huber"


# ---------------------------------------------------------------------------
# Metric calibration provenance: real reference, explicit dev opt-in, refusal
# ---------------------------------------------------------------------------


def _no_dev_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("DW_DEV_CALIBRATION", None)
    env.setdefault("PYTHONPATH", "src")
    return env


def _write_gcps(path: Path) -> Path:
    path.write_text(
        "pixel_col,pixel_row,elevation\n0,0,101\n4,0,104\n0,3,107\n4,3,112\n2,1,105.5\n"
    )
    return path


def _bridge_without_dev(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BRIDGE), *args],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        env=_no_dev_env(),
        timeout=300,
    )


def test_metric_terrain_file_without_reference_is_refused(tmp_path: Path) -> None:
    """No reference and no dev opt-in: metric output fails, never fabricates metres."""
    make_png(tmp_path / "a.png")
    proc = _bridge_without_dev("--terrain-file", str(tmp_path / "a.png"))
    assert proc.returncode != 0
    payload = json.loads(proc.stdout)
    assert payload["type"] == "CalibrationError"
    assert "calibration reference" in payload["error"]


def test_metric_terrain_file_calibrates_against_gcp_reference(tmp_path: Path) -> None:
    """A GCP CSV on a georeferenced input yields a really-calibrated DSM."""
    scene = make_geotiff(tmp_path / "scene.tif")
    gcps = _write_gcps(tmp_path / "gcps.csv")
    proc = _bridge_without_dev(
        "--backend",
        "synthetic-depth",
        "--reference",
        str(gcps),
        "--calibration-method",
        "scale_offset",
        "--terrain-file",
        str(scene),
    )
    assert proc.returncode == 0, proc.stdout[-2000:]
    payload = json.loads(proc.stdout)
    assert payload["dsm"]["units"] == "meters"
    assert payload["mesh"]["calibration_reference"] == "gcps.csv"
    assert payload["mesh"]["calibration_valid_samples"] == 5


def test_relative_terrain_file_needs_no_reference(tmp_path: Path) -> None:
    """Relative mode never calibrates, so it runs without any reference."""
    make_png(tmp_path / "a.png")
    proc = _bridge_without_dev("--mode", "relative", "--terrain-file", str(tmp_path / "a.png"))
    assert proc.returncode == 0, proc.stdout[-2000:]
    payload = json.loads(proc.stdout)
    assert payload["rsm"]["units"] is None


def _service_handle(payload: dict[str, object], dev: bool) -> dict[str, object]:
    code = (
        "import json, sys; sys.path.insert(0, 'scripts');"
        "from depthwiz_service import handle_request;"
        "print(json.dumps(handle_request(json.loads(sys.stdin.read()))))"
    )
    env = _no_dev_env()
    env["PYTHONPATH"] = "src"
    if dev:
        env["DW_DEV_CALIBRATION"] = "1"
    proc = subprocess.run(
        [sys.executable, "-c", code],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        env=env,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    result: dict[str, object] = json.loads(proc.stdout)
    return result


def test_service_metric_without_reference_fails_at_calibration(tmp_path: Path) -> None:
    make_png(tmp_path / "a.png")
    result = _service_handle(
        {"input_path": str(tmp_path / "a.png"), "target_semantics": "absolute_elevation_dsm"},
        dev=False,
    )
    response = result["response"]
    assert isinstance(response, dict)
    assert response["success"] is False
    assert response["failure"]["code"] == "CalibrationError"
    assert response["failure"]["stage"] == "calibrating"


def test_service_metric_uses_request_reference(tmp_path: Path) -> None:
    scene = make_geotiff(tmp_path / "scene.tif")
    gcps = _write_gcps(tmp_path / "gcps.csv")
    result = _service_handle(
        {
            "input_path": str(scene),
            "target_semantics": "absolute_elevation_dsm",
            "calibration_reference_path": str(gcps),
            "calibration_method": "scale_offset_huber",
            "build_mesh": True,
        },
        dev=False,
    )
    response = result["response"]
    assert isinstance(response, dict)
    assert response["success"] is True, response["failure"]
    assert response["summary"]["calibration_reference"] == "gcps.csv"
    assert response["summary"]["calibration_method"] == "scale_offset_huber"


def test_service_dev_calibration_is_explicit_and_labelled(tmp_path: Path) -> None:
    make_png(tmp_path / "a.png")
    result = _service_handle(
        {"input_path": str(tmp_path / "a.png"), "target_semantics": "absolute_elevation_dsm"},
        dev=True,
    )
    response = result["response"]
    assert isinstance(response, dict)
    assert response["success"] is True
    assert response["summary"]["calibration_reference"] == "synthetic-dev-ref"


def test_misspelt_option_is_rejected() -> None:
    """A typo such as --calibraton-method must not become a positional value."""
    proc = run_bridge("--calibraton-method", "piecewise_linear", "--terrain", "4", "4")
    assert proc.returncode != 0
    assert "unknown option '--calibraton-method'" in json.loads(proc.stdout)["error"]
