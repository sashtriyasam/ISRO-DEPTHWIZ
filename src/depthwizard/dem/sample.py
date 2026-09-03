"""Deterministic nearest-neighbour terrain sampling (no interpolation).

Pixel sampling addresses integer cells (pixel-center semantics);
world sampling converts through S7 without silent rounding and then
applies the same explicit nearest policy. Out-of-bounds and nodata
locations yield explicit invalid results — never clamped, wrapped,
or invented. Bilinear interpolation is deliberately absent (future
work documents itself when it lands).
"""

from __future__ import annotations

import math

from depthwizard.dem.models import TerrainReferenceGrid, TerrainSample
from depthwizard.geospatial.transforms import pixel_to_world, world_to_pixel


def sample_terrain(grid: TerrainReferenceGrid, row: int, col: int) -> TerrainSample:
    """Sample the integer cell (row, col) with pixel-center semantics."""
    if not isinstance(grid, TerrainReferenceGrid):
        raise TypeError(
            f"sample_terrain requires a TerrainReferenceGrid; got {type(grid).__name__}"
        )
    if (
        not isinstance(row, int)
        or not isinstance(col, int)
        or isinstance(row, bool)
        or isinstance(col, bool)
    ):
        raise TypeError(f"pixel sampling requires integer row/col, got {row!r}, {col!r}")
    if row < 0 or col < 0 or row >= grid.height or col >= grid.width:
        return TerrainSample(valid=False, reference_id=grid.source_dem_id)
    x, y = pixel_to_world(grid.transform, float(col), float(row))
    if not bool(grid.valid_mask[row, col]):
        return TerrainSample(
            valid=False,
            row=row,
            col=col,
            pixel_row=float(row),
            pixel_col=float(col),
            x=x,
            y=y,
            reference_id=grid.source_dem_id,
        )
    elevation = float(grid.array[row, col])
    if not math.isfinite(elevation):
        return TerrainSample(
            valid=False,
            row=row,
            col=col,
            pixel_row=float(row),
            pixel_col=float(col),
            x=x,
            y=y,
            reference_id=grid.source_dem_id,
        )
    return TerrainSample(
        valid=True,
        elevation=elevation,
        row=row,
        col=col,
        pixel_row=float(row),
        pixel_col=float(col),
        x=x,
        y=y,
        reference_id=grid.source_dem_id,
    )


def sample_terrain_at_world(grid: TerrainReferenceGrid, x: float, y: float) -> TerrainSample:
    """Sample at world coordinates with explicit nearest-cell policy.

    Continuous pixel coordinates come from S7 (unrounded, corner-based:
    integer values are cell corners). The containing cell is ``floor``
    of each coordinate — deterministic, with exact corners belonging to
    the upper cell by half-open convention. This equals nearest-center
    sampling everywhere except exact corner ties, which resolve
    deterministically rather than by hidden rounding.
    """
    if not isinstance(grid, TerrainReferenceGrid):
        raise TypeError(
            f"sample_terrain_at_world requires a TerrainReferenceGrid; got {type(grid).__name__}"
        )
    for name, value in (("x", x), ("y", y)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"world sampling requires numeric {name}, got {value!r}")
        if not math.isfinite(float(value)):
            raise TypeError(f"world sampling requires finite {name}, got {value!r}")
    cont_col, cont_row = world_to_pixel(grid.transform, float(x), float(y))
    row, col = math.floor(cont_row), math.floor(cont_col)
    if row < 0 or col < 0 or row >= grid.height or col >= grid.width:
        return TerrainSample(
            valid=False,
            pixel_row=cont_row,
            pixel_col=cont_col,
            x=float(x),
            y=float(y),
            reference_id=grid.source_dem_id,
        )
    resolved = sample_terrain(grid, row, col)
    return resolved.model_copy(
        update={
            "pixel_row": cont_row,
            "pixel_col": cont_col,
            "x": float(x),
            "y": float(y),
        }
    )
