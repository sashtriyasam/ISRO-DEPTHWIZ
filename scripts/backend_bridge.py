#!/usr/bin/env python3
"""Backend execution bridge: TypeScript → Python → backend products → JSON.

This script executes the ACTUAL depthwizard backend subsystems and outputs
serialized products as JSON to stdout.

Architecture:
  TypeScript (bridge.ts)
    → spawns this Python script
    → this script runs real backend code (no reimplementation)
    → outputs JSON to stdout
    → TypeScript parses, validates, adapts

Modes:
  python scripts/backend_bridge.py <input_image_path>
      DepthResult for a real input file.
  python scripts/backend_bridge.py --synthetic <width> <height>
      DepthResult for a generated synthetic input (depth-only path).
  python scripts/backend_bridge.py --terrain <width> <height>
      Full terrain chain for a generated synthetic input:
        synthetic input
        → SyntheticDepthBackend.estimate_depth()
        → deterministic dev calibration (scale_offset)
        → create_scientific_height_product()
        → rasterize_height_product()  (DSMGrid)
        → build_terrain_mesh()        (TerrainMesh)
      Outputs depth_result + dsm + mesh. All values are produced by the
      real backend subsystems; this script only orchestrates and serializes.

IMPORTANT: This script requires the depthwizard package to be installed.
It does NOT contain a duplicate implementation of any backend behavior.
The dev calibration mirrors tests/height/support.py::exact_calibration
(the sanctioned deterministic dev calibration); the fit itself is computed
by the real ScaleOffsetCalibrator.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dw_serialize import serialize_terrain

# ---------------------------------------------------------------------------
# Import the ACTUAL depthwizard backend — no fallback, no duplicate formulas
# ---------------------------------------------------------------------------

try:
    from depthwizard.backends.synthetic import SyntheticDepthBackend
    from depthwizard.calibration import (
        CalibrationSamples,
        ScaleOffsetCalibrator,
    )
    from depthwizard.contracts.semantics import ElevationSemantics
    from depthwizard.dsm.rasterize import rasterize_height_product
    from depthwizard.height import create_scientific_height_product
    from depthwizard.ingestion.api import inspect_input
    from depthwizard.mesh.build import build_terrain_mesh
except ImportError as exc:
    print(
        json.dumps(
            {
                "error": (
                    "depthwizard package not installed. "
                    "Install it with: pip install -e .  "
                    f"Original error: {exc}"
                ),
                "type": "ImportError",
            }
        )
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Deterministic dev calibration reference (mirrors the sanctioned backend
# test helper tests/height/support.py::exact_calibration).
# ---------------------------------------------------------------------------

DEV_REFERENCE_ID = "synthetic-dev-ref"
DEV_PREDICTED = (0.0, 1.0, 2.0, 3.0, 4.0)
DEV_REFERENCE = (10.0, 12.5, 15.0, 17.5, 20.0)  # exact 2.5x + 10 mapping
DEV_TARGET_SEMANTICS = ElevationSemantics.ABSOLUTE_ELEVATION_DSM


def create_synthetic_png(width: int, height: int, path: Path) -> Path:
    """Create a deterministic synthetic PNG for testing using Pillow."""
    from PIL import Image

    img = Image.new("RGB", (width, height))
    pixels = img.load()
    assert pixels is not None
    for row in range(height):
        for col in range(width):
            v = 255 if (row + col) % 2 == 0 else 0
            pixels[col, row] = (v, (col * 32) % 256, (row * 40) % 256)
    img.save(path, format="PNG")
    return path


def emit_stage(name: str) -> None:
    """Report a genuinely completed backend stage (stderr, never stdout).

    Consumers parse lines starting with ``STAGE ``. A line is emitted
    only after the corresponding backend stage has actually finished —
    never speculatively, never on a timer.
    """
    print(f"STAGE {name}", file=sys.stderr, flush=True)


def run_depth_only(width: int, height: int) -> dict:
    """Depth-only path: synthetic input → DepthResult."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        create_synthetic_png(width, height, tmp_path)
        inspection = inspect_input(tmp_path)
        emit_stage("preprocessing")
        result = SyntheticDepthBackend().estimate_depth(inspection)
        emit_stage("inference_running")
        return result.model_dump()
    finally:
        tmp_path.unlink(missing_ok=True)


def run_terrain(width: int, height: int) -> dict:
    """Full terrain chain on a generated synthetic input."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        create_synthetic_png(width, height, tmp_path)
        return run_terrain_on_path(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def run_terrain_on_path(input_path: Path) -> dict:
    """Full terrain chain on a real input file using only real backend subsystems."""
    inspection = inspect_input(input_path)
    emit_stage("preprocessing")
    depth = SyntheticDepthBackend().estimate_depth(inspection)
    emit_stage("inference_running")

    samples = CalibrationSamples(
        predicted_values=DEV_PREDICTED,
        reference_values=DEV_REFERENCE,
        reference_id=DEV_REFERENCE_ID,
        reference_units="meters",
        target_semantics=DEV_TARGET_SEMANTICS,
        source_checksum=inspection.handle.sha256,
    )
    calibration = ScaleOffsetCalibrator().calibrate(samples)

    emit_stage("calibrating")
    product = create_scientific_height_product(depth, calibration, DEV_TARGET_SEMANTICS)
    grid = rasterize_height_product(product)
    emit_stage("dsm_generation")
    mesh = build_terrain_mesh(grid)
    emit_stage("mesh_generation")

    return serialize_terrain(depth, grid, mesh)


def run_capabilities() -> dict:
    """Report actual backend input capabilities (no input needed)."""
    from depthwizard.ingestion.formats import SUPPORTED_SUFFIXES

    return {
        "contract_version": "1",
        "supported_suffixes": list(SUPPORTED_SUFFIXES),
    }


def run_inspect(input_path: Path) -> dict:
    """Validate one real input file with the actual backend ingestion."""
    from depthwizard.errors import DepthWizardError

    if not input_path.exists():
        return {
            "valid": False,
            "failure": {
                "code": "invalid_input",
                "message": f"Input file not found: {input_path.name}",
            },
        }
    try:
        inspection = inspect_input(input_path)
        return {"valid": True, "inspection": inspection.model_dump(mode="json")}
    except DepthWizardError as exc:
        return {
            "valid": False,
            "failure": {"code": exc.code, "message": str(exc)},
        }
    except ImportError as exc:
        return {
            "valid": False,
            "failure": {
                "code": "environment_unsupported",
                "message": f"Backend reader unavailable in this environment: {exc}",
            },
        }


def main() -> None:
    """Main entry point: invoke the actual backend and serialize the result."""
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {
                    "error": (
                        "Usage: backend_bridge.py <input_path> | --synthetic <w> <h> "
                        "| --terrain <w> <h> | --terrain-file <path> "
                        "| --inspect <path> | --capabilities"
                    )
                }
            )
        )
        sys.exit(1)

    try:
        if sys.argv[1] == "--terrain":
            width = int(sys.argv[2]) if len(sys.argv) > 2 else 8
            height = int(sys.argv[3]) if len(sys.argv) > 3 else 8
            print(json.dumps(run_terrain(width, height), allow_nan=False))
        elif sys.argv[1] == "--terrain-file":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Missing input path for --terrain-file"}))
                sys.exit(1)
            input_path = Path(sys.argv[2])
            if not input_path.exists():
                print(json.dumps({"error": f"Input file not found: {input_path}"}))
                sys.exit(1)
            print(json.dumps(run_terrain_on_path(input_path), allow_nan=False))
        elif sys.argv[1] == "--inspect":
            if len(sys.argv) < 3:
                print(json.dumps({"error": "Missing input path for --inspect"}))
                sys.exit(1)
            print(json.dumps(run_inspect(Path(sys.argv[2]))))
        elif sys.argv[1] == "--capabilities":
            print(json.dumps(run_capabilities()))
        elif sys.argv[1] == "--synthetic":
            width = int(sys.argv[2]) if len(sys.argv) > 2 else 8
            height = int(sys.argv[3]) if len(sys.argv) > 3 else 8
            print(json.dumps(run_depth_only(width, height)))
        else:
            input_path = Path(sys.argv[1])
            if not input_path.exists():
                print(json.dumps({"error": f"Input file not found: {input_path}"}))
                sys.exit(1)

            inspection = inspect_input(input_path)
            result = SyntheticDepthBackend().estimate_depth(inspection)
            print(json.dumps(result.model_dump()))

    except Exception as e:
        print(json.dumps({"error": str(e), "type": type(e).__name__}))
        sys.exit(1)


if __name__ == "__main__":
    main()
