"""Coordinates, UVs, mapping, provenance, immutability, determinism."""

import numpy as np
import pytest
from pydantic import ValidationError

from depthwizard.contracts.semantics import ElevationSemantics, GeoreferencingLevel
from depthwizard.contracts.spatial import SpatialKind
from depthwizard.mesh import CoordinateFrame, build_terrain_mesh
from tests.mesh.support import GEO_AFFINE, GEO_CRS, flat_dsm, holed_dsm


def test_georeferenced_coordinates() -> None:
    mesh = build_terrain_mesh(holed_dsm(5, 4, 3.0, set(), georef=True))
    assert mesh.frame is CoordinateFrame.GEOREFERENCED_LOCAL
    assert mesh.origin_x == GEO_AFFINE[0] == 100.0
    assert mesh.origin_y == GEO_AFFINE[3] == 200.0
    assert mesh.spatial.details is not None
    assert mesh.spatial.details.crs == GEO_CRS
    # Pixel (r=0, c=0) center through the GDAL-order affine, minus origin.
    assert mesh.vertices[0].tolist() == pytest.approx([0.25, 3.0, -0.25])
    # Pixel (r=3, c=4): x = 0.5*4.5, z = -0.5*3.5.
    assert mesh.vertices[19].tolist() == pytest.approx([2.25, 3.0, -1.75])
    # Reconstruction reproduces world coordinates.
    assert mesh.vertices[0][0] + mesh.origin_x == pytest.approx(100.25)
    assert mesh.vertices[0][2] + mesh.origin_y == pytest.approx(199.75)
    assert mesh.georeferencing is GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE


def test_local_coordinates_no_crs_claims() -> None:
    mesh = build_terrain_mesh(flat_dsm(5, 4, 3.0))
    assert mesh.frame is CoordinateFrame.LOCAL
    assert mesh.origin_x is None
    assert mesh.origin_y is None
    assert mesh.spatial.kind is SpatialKind.NOT_APPLICABLE
    assert mesh.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED


def test_uv_convention() -> None:
    mesh = build_terrain_mesh(flat_dsm(3, 2, 0.0))
    assert mesh.uvs[0].tolist() == [0.0, 0.0]
    assert mesh.uvs[2].tolist() == [1.0, 0.0]
    assert mesh.uvs[3].tolist() == [0.0, 1.0]
    assert mesh.uvs[5].tolist() == [1.0, 1.0]
    assert bool(((mesh.uvs >= 0.0) & (mesh.uvs <= 1.0)).all())


def test_source_mapping_correct() -> None:
    mesh = build_terrain_mesh(holed_dsm(4, 4, 1.0, {(1, 1)}))
    assert len(mesh.vertex_source_indices) == mesh.vertex_count == 15
    # Row-major order preserved: sources ascend, hole pixel 5 absent.
    assert mesh.vertex_source_indices.tolist() == [i for i in range(16) if i != 5]
    for triangle in mesh.indices.reshape(-1, 3).tolist():
        for vertex in triangle:
            assert mesh.vertex_source_indices[vertex] != 5


def test_semantics_and_provenance_preserved() -> None:
    mesh = build_terrain_mesh(
        flat_dsm(3, 3, 1.0, semantics=ElevationSemantics.ABSOLUTE_ELEVATION_DSM)
    )
    assert mesh.semantics is ElevationSemantics.ABSOLUTE_ELEVATION_DSM
    assert mesh.units == "meters"
    assert mesh.depth_model_name == "test-backend"
    assert mesh.calibration_method == "scale_offset"
    assert mesh.calibration_reference == "ref-test"
    assert (mesh.calibration_scale, mesh.calibration_offset) == (1.0, 0.0)
    assert not hasattr(mesh, "vertical_datum")


def test_sources_unchanged() -> None:
    grid = holed_dsm(4, 4, 1.0, {(1, 1)})
    array_before = grid.array.copy()
    mask_before = grid.valid_mask.copy()
    build_terrain_mesh(grid)
    assert bool(np.array_equal(grid.array, array_before, equal_nan=True))
    assert bool((grid.valid_mask == mask_before).all())


def test_meshes_independent_and_deterministic() -> None:
    grid = flat_dsm(3, 3, 2.0)
    first = build_terrain_mesh(grid)
    first.vertices[0, 1] = -999.0
    second = build_terrain_mesh(grid)
    assert second.vertices[0, 1] == 2.0
    third = build_terrain_mesh(grid)
    assert bool(np.array_equal(second.vertices, third.vertices))
    assert bool(np.array_equal(second.indices, third.indices))
    assert bool(np.array_equal(second.normals, third.normals))
    assert bool(np.array_equal(second.uvs, third.uvs))
    assert second.model_dump(
        exclude={"vertices", "indices", "normals", "uvs", "vertex_source_indices"}
    ) == third.model_dump(
        exclude={"vertices", "indices", "normals", "uvs", "vertex_source_indices"}
    )


def test_mesh_model_frozen() -> None:
    mesh = build_terrain_mesh(flat_dsm(2, 2, 1.0))
    with pytest.raises(ValidationError):
        mesh.coverage = 0.5
