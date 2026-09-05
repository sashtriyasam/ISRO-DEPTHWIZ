"""Deterministic regular-grid triangulation of DSM grids (no renderers).

One vertex per valid pixel (compacted, row-major), two triangles per
fully valid quad, area-weighted accumulated normals with a vertical
fallback, normalized UVs. Holes are never bridged: a triangle exists
only if all its source pixels are valid. Winding is a deterministic
function of the planar mapping handedness so normals face upward in
both axis-aligned and north-up (flipped) frames.
"""

from __future__ import annotations

import numpy as np

from depthwizard.dsm.grid import DSMGrid
from depthwizard.errors import MeshGenerationError
from depthwizard.mesh.models import CoordinateFrame, TerrainMesh

_FALLBACK_NORMAL = (0.0, 1.0, 0.0)


def _planar_coordinates(
    grid: DSMGrid, cols: np.ndarray, rows: np.ndarray
) -> tuple[np.ndarray, np.ndarray, CoordinateFrame, float | None, float | None, bool]:
    """Horizontal positions, frame, origin and winding-flip flag.

    Georeferenced grids use pixel centers through the stored GDAL-order
    affine, expressed relative to the raster origin (translation terms)
    so vertex coordinates stay small and reconstructible. Anything else
    uses deterministic pixel-local coordinates with no CRS claims.
    """
    details = grid.spatial.details
    transform = details.transform if details is not None else None
    cols_f = cols.astype(np.float64)
    rows_f = rows.astype(np.float64)
    if transform is not None:
        a, b, c, d, e, f = (
            transform.a,
            transform.b,
            transform.c,
            transform.d,
            transform.e,
            transform.f,
        )
        det = b * f - c * e
        if det == 0.0:
            raise MeshGenerationError(
                "degenerate planar mapping: raster transform has zero "
                "determinant, pixel positions collapse (no valid 2D frame)"
            )
        world_x = a + b * (cols_f + 0.5) + c * (rows_f + 0.5)
        world_z = d + e * (cols_f + 0.5) + f * (rows_f + 0.5)
        return (
            world_x - a,
            world_z - d,
            CoordinateFrame.GEOREFERENCED_LOCAL,
            a,
            d,
            det < 0.0,
        )
    return cols_f, rows_f, CoordinateFrame.LOCAL, None, None, False


def _triangulate_surface(
    values: np.ndarray,
    valid: np.ndarray,
    plane_x: np.ndarray,
    plane_z: np.ndarray,
    flip: bool,
    width: int,
    height: int,
) -> dict[str, np.ndarray | int | float]:
    """Shared regular-grid triangulation core (DSM and relative paths).

    One vertex per valid pixel (compacted, row-major), two triangles per
    fully valid quad, area-weighted accumulated normals with a vertical
    fallback, normalized UVs. Holes are never bridged. Operates purely
    on arrays; all contract interpretation stays with the callers.
    """
    valid_count = int(valid.sum())
    invalid_count = width * height - valid_count
    if height < 2 or width < 2:
        raise MeshGenerationError(
            f"mesh needs at least a 2x2 grid for quad topology; "
            f"got {width}x{height} ({valid_count} valid pixels)"
        )
    if valid_count == 0:
        raise MeshGenerationError(
            f"mesh needs valid source pixels; grid {width}x{height} "
            f"has {invalid_count} invalid and 0 valid"
        )
    index_of = np.full((height, width), -1, dtype=np.int64)
    index_of[valid] = np.arange(valid_count, dtype=np.int64)
    rows, cols = np.nonzero(valid)
    source_indices = (rows.astype(np.int64) * width + cols.astype(np.int64)).astype(np.int64)
    elevation = values[valid].astype(np.float64)
    vertices = np.stack([plane_x, elevation, plane_z], axis=1)
    corner_00 = valid[:-1, :-1]
    corner_01 = valid[:-1, 1:]
    corner_10 = valid[1:, :-1]
    corner_11 = valid[1:, 1:]
    quad_ok = corner_00 & corner_01 & corner_10 & corner_11
    quad_total = (height - 1) * (width - 1)
    quad_used = int(quad_ok.sum())
    skipped = quad_total - quad_used
    if quad_used == 0:
        raise MeshGenerationError(
            f"no usable quad topology: {valid_count} valid but no complete "
            f"2x2 quad in {width}x{height} ({invalid_count} invalid pixels); "
            "holes are never bridged"
        )
    i00 = index_of[:-1, :-1][quad_ok]
    i01 = index_of[:-1, 1:][quad_ok]
    i10 = index_of[1:, :-1][quad_ok]
    i11 = index_of[1:, 1:][quad_ok]
    first = np.stack([i00, i10, i01], axis=1)
    second = np.stack([i10, i11, i01], axis=1)
    triangles = np.empty((2 * quad_used, 3), dtype=np.int64)
    triangles[0::2] = first
    triangles[1::2] = second
    if flip:
        triangles = triangles[:, (0, 2, 1)]
    edges_a = vertices[triangles[:, 1]] - vertices[triangles[:, 0]]
    edges_b = vertices[triangles[:, 2]] - vertices[triangles[:, 0]]
    faces = np.cross(edges_a, edges_b)
    normals = np.zeros((valid_count, 3), dtype=np.float64)
    np.add.at(normals, triangles.ravel(), np.repeat(faces, 3, axis=0))
    lengths = np.sqrt((normals**2).sum(axis=1))
    nonzero = lengths > 0.0
    normals[nonzero] /= lengths[nonzero, np.newaxis]
    normals[~nonzero] = _FALLBACK_NORMAL
    if not bool(np.isfinite(vertices).all()) or not bool(np.isfinite(normals).all()):
        raise MeshGenerationError(
            "non-finite mesh geometry generated; refusing to publish NaN normals "
            f"or positions ({width}x{height}, {valid_count} valid pixels)"
        )
    unit_w = (
        cols.astype(np.float64) / (width - 1)
        if width > 1
        else np.zeros_like(cols, dtype=np.float64)
    )
    unit_h = (
        rows.astype(np.float64) / (height - 1)
        if height > 1
        else np.zeros_like(rows, dtype=np.float64)
    )
    uvs = np.stack([unit_w, unit_h], axis=1)
    triangle_total = 2 * quad_used
    coverage = triangle_total / (2 * quad_total)
    return {
        "vertices": vertices,
        "indices": triangles.ravel(),
        "normals": normals,
        "uvs": uvs,
        "vertex_source_indices": source_indices,
        "vertex_count": valid_count,
        "triangle_count": triangle_total,
        "valid_source_pixels": valid_count,
        "invalid_source_pixels": invalid_count,
        "skipped_cells": skipped,
        "coverage": coverage,
    }


def build_terrain_mesh(grid: DSMGrid) -> TerrainMesh:
    """Build an owned terrain mesh from a validated DSM grid.

    Never mutates the source grid. Raises :class:`MeshGenerationError`
    for degenerate dimensions, absent valid pixels, unusable topology
    or non-finite generated geometry.
    """
    if not isinstance(grid, DSMGrid):
        raise TypeError(f"build_terrain_mesh requires a DSMGrid; got {type(grid).__name__}")
    height, width = grid.height, grid.width
    valid = grid.valid_mask
    rows, cols = np.nonzero(valid)
    local_x, local_z, frame, origin_x, origin_y, flip = _planar_coordinates(grid, cols, rows)
    surface = _triangulate_surface(grid.array, valid, local_x, local_z, flip, width, height)
    assert isinstance(surface["vertices"], np.ndarray)
    return TerrainMesh(
        vertices=surface["vertices"],
        indices=surface["indices"],  # type: ignore[arg-type]
        normals=surface["normals"],  # type: ignore[arg-type]
        uvs=surface["uvs"],  # type: ignore[arg-type]
        vertex_source_indices=surface["vertex_source_indices"],  # type: ignore[arg-type]
        vertex_count=int(surface["vertex_count"]),
        triangle_count=int(surface["triangle_count"]),
        valid_source_pixels=int(surface["valid_source_pixels"]),
        invalid_source_pixels=int(surface["invalid_source_pixels"]),
        skipped_cells=int(surface["skipped_cells"]),
        coverage=float(surface["coverage"]),
        frame=frame,
        origin_x=origin_x,
        origin_y=origin_y,
        width=width,
        height=height,
        units=grid.units,
        semantics=grid.semantics,
        georeferencing=grid.georeferencing,
        spatial=grid.spatial,
        depth_model_name=grid.depth_model_name,
        depth_model_version=grid.depth_model_version,
        depth_checkpoint_id=grid.depth_checkpoint_id,
        source_input_id=grid.source_input_id,
        source_checksum=grid.source_checksum,
        calibration_method=grid.calibration_method,
        calibration_reference=grid.calibration_reference,
        calibration_scale=grid.calibration_scale,
        calibration_offset=grid.calibration_offset,
        calibration_valid_samples=grid.calibration_valid_samples,
        provenance=grid.provenance,
    )
