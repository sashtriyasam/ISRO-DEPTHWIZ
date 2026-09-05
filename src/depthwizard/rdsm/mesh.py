"""Relative surface meshing: rDSM grid → pixel-local mesh.

Shares the canonical triangulation core with the metric DSM path
(same topology, normals, UVs, hole policy). The relative mesh always
uses the pixel-local frame — even when the source carries a CRS, the
relative surface never places pixels in the world.
"""

from __future__ import annotations

import numpy as np

from depthwizard.mesh.build import _triangulate_surface
from depthwizard.mesh.models import CoordinateFrame
from depthwizard.rdsm.models import RelativeSurfaceGrid as RelativeSurfaceGrid
from depthwizard.rdsm.models import RelativeTerrainMesh as RelativeTerrainMesh


def build_relative_mesh(grid: RelativeSurfaceGrid) -> RelativeTerrainMesh:
    """Build an owned relative mesh from a validated rDSM grid.

    Never mutates the source grid. Raises :class:`MeshGenerationError`
    for degenerate dimensions, absent valid pixels, unusable topology
    or non-finite generated geometry (same rules as the metric path).
    """
    if not isinstance(grid, RelativeSurfaceGrid):
        raise TypeError(
            f"build_relative_mesh requires a RelativeSurfaceGrid; got {type(grid).__name__}"
        )
    height, width = grid.height, grid.width
    valid = grid.valid_mask
    rows, cols = np.nonzero(valid)
    plane_x = cols.astype(np.float64)
    plane_z = rows.astype(np.float64)
    surface = _triangulate_surface(grid.array, valid, plane_x, plane_z, False, width, height)
    assert isinstance(surface["vertices"], np.ndarray)
    return RelativeTerrainMesh(
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
        frame=CoordinateFrame.LOCAL,
        width=width,
        height=height,
        units=None,
        semantics=grid.semantics,
        georeferencing=grid.georeferencing,
        spatial=grid.spatial,
        depth_model_name=grid.depth_model_name,
        depth_model_version=grid.depth_model_version,
        depth_checkpoint_id=grid.depth_checkpoint_id,
        source_input_id=grid.source_input_id,
        source_checksum=grid.source_checksum,
        provenance=grid.provenance,
    )
