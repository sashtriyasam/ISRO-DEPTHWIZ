"""Shared JSON serialization helpers for the dev bridge scripts.

Pure transport utilities only: float sanitizing, array flattening, and
the terrain-payload shape consumed by the TypeScript frontend. No
science lives here — all values come from real backend objects passed
in by the caller.
"""

from __future__ import annotations

import math
from typing import Any


def json_num(value: float) -> float | None:
    """Map non-finite floats (NaN nodata) to null for strict JSON output."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def json_list(values: Any) -> list[Any]:
    """Flatten an array-like to a JSON-safe list (NaN → null)."""
    import numpy as _np

    flat = _np.asarray(values).ravel()
    if flat.dtype.kind == "f":
        return [json_num(float(v)) for v in flat]
    return [v.item() if hasattr(v, "item") else v for v in flat]


FULL_TERRAIN_STAGES = [
    "preprocessing",
    "inference_running",
    "calibrating",
    "dsm_generation",
    "mesh_generation",
]


def serialize_terrain(
    depth: Any, grid: Any, mesh: Any, stages: list[str] | None = None
) -> dict[str, Any]:
    """Serialize a depth result + DSM grid + terrain mesh to the frontend shape.

    ``stages`` records the backend stages that actually ran; callers
    must pass the real history (the default covers the legacy
    all-stages path only).
    """
    spatial_dump = mesh.spatial.model_dump()
    provenance_dump = mesh.provenance.model_dump(mode="json")
    return {
        "kind": "terrain",
        "stages": list(stages) if stages is not None else list(FULL_TERRAIN_STAGES),
        "depth_result": depth.model_dump(),
        "dsm": {
            "width": grid.width,
            "height": grid.height,
            "dtype": grid.dtype,
            "units": grid.units,
            "semantics": grid.semantics.value,
            "values": json_list(grid.array),
            "valid_mask": [bool(v) for v in grid.valid_mask.ravel()],
            "invalid_count": grid.invalid_count,
            "nodata": None,
            "georeferencing": grid.georeferencing.value,
            "spatial": grid.spatial.model_dump(),
        },
        "mesh": {
            "vertices": json_list(mesh.vertices),
            "indices": json_list(mesh.indices),
            "normals": json_list(mesh.normals),
            "uvs": json_list(mesh.uvs),
            "vertex_source_indices": json_list(mesh.vertex_source_indices),
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
