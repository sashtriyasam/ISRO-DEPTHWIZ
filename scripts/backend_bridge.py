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
import math
import sys
import tempfile
from pathlib import Path
from typing import Any

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
    print(json.dumps({
        "error": (
            "depthwizard package not installed. "
            "Install it with: pip install -e .  "
            f"Original error: {exc}"
        ),
        "type": "ImportError",
    }))
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


def _json_num(value: float) -> float | None:
    """Map non-finite floats (NaN nodata) to null for strict JSON output."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _json_list(values: Any) -> list:
    """Flatten an array-like to a JSON-safe list (NaN → null)."""
    import numpy as _np

    flat = _np.asarray(values).ravel()
    if flat.dtype.kind == "f":
        return [_json_num(float(v)) for v in flat]
    return [v.item() if hasattr(v, "item") else v for v in flat]


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
    """Full terrain chain using only real backend subsystems."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        create_synthetic_png(width, height, tmp_path)
        inspection = inspect_input(tmp_path)
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
        product = create_scientific_height_product(
            depth, calibration, DEV_TARGET_SEMANTICS
        )
        grid = rasterize_height_product(product)
        emit_stage("dsm_generation")
        mesh = build_terrain_mesh(grid)
        emit_stage("mesh_generation")

        spatial_dump = mesh.spatial.model_dump()
        provenance_dump = mesh.provenance.model_dump(mode="json")

        return {
            "kind": "terrain",
            "stages": [
                "preprocessing",
                "inference_running",
                "calibrating",
                "dsm_generation",
                "mesh_generation",
            ],
            "depth_result": depth.model_dump(),
            "dsm": {
                "width": grid.width,
                "height": grid.height,
                "dtype": grid.dtype,
                "units": grid.units,
                "semantics": grid.semantics.value,
                "values": _json_list(grid.array),
                "valid_mask": [bool(v) for v in grid.valid_mask.ravel()],
                "invalid_count": grid.invalid_count,
                "nodata": None,
                "georeferencing": grid.georeferencing.value,
                "spatial": spatial_dump,
            },
            "mesh": {
                "vertices": _json_list(mesh.vertices),
                "indices": _json_list(mesh.indices),
                "normals": _json_list(mesh.normals),
                "uvs": _json_list(mesh.uvs),
                "vertex_source_indices": _json_list(mesh.vertex_source_indices),
                "vertex_count": mesh.vertex_count,
                "triangle_count": mesh.triangle_count,
                "valid_source_pixels": mesh.valid_source_pixels,
                "invalid_source_pixels": mesh.invalid_source_pixels,
                "skipped_cells": mesh.skipped_cells,
                "coverage": float(mesh.coverage),
                "frame": mesh.frame.value,
                "origin_x": mesh.origin_x,
                "origin_y": mesh.origin_y,
                "width": mesh.width,
                "height": mesh.height,
                "units": mesh.units,
                "semantics": mesh.semantics.value,
                "georeferencing": mesh.georeferencing.value,
                "spatial": spatial_dump,
                "depth_model_name": mesh.depth_model_name,
                "depth_model_version": mesh.depth_model_version,
                "depth_checkpoint_id": mesh.depth_checkpoint_id,
                "source_input_id": mesh.source_input_id,
                "source_checksum": mesh.source_checksum,
                "calibration_method": mesh.calibration_method,
                "calibration_reference": mesh.calibration_reference,
                "calibration_scale": mesh.calibration_scale,
                "calibration_offset": mesh.calibration_offset,
                "calibration_valid_samples": mesh.calibration_valid_samples,
                "provenance": provenance_dump,
            },
        }
    finally:
        tmp_path.unlink(missing_ok=True)


def main() -> None:
    """Main entry point: invoke the actual backend and serialize the result."""
    if len(sys.argv) < 2:
        print(json.dumps({
            "error": "Usage: backend_bridge.py <input_path> | --synthetic <w> <h> | --terrain <w> <h>"
        }))
        sys.exit(1)

    try:
        if sys.argv[1] == "--terrain":
            width = int(sys.argv[2]) if len(sys.argv) > 2 else 8
            height = int(sys.argv[3]) if len(sys.argv) > 3 else 8
            print(json.dumps(run_terrain(width, height), allow_nan=False))
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
