"""Topology: counts, winding, mapping, coverage on fully valid grids."""

from depthwizard.mesh import TerrainMesh, build_terrain_mesh
from tests.mesh.support import flat_dsm


def test_flat_3x3_topology() -> None:
    mesh = build_terrain_mesh(flat_dsm(3, 3, 5.0))
    assert isinstance(mesh, TerrainMesh)
    assert mesh.vertex_count == 9
    assert mesh.triangle_count == 8  # 2 * (3-1) * (3-1)
    assert mesh.valid_source_pixels == 9
    assert mesh.invalid_source_pixels == 0
    assert mesh.skipped_cells == 0
    assert mesh.coverage == 1.0
    assert tuple(mesh.vertex_source_indices.tolist()) == tuple(range(9))
    assert len(mesh.indices) == 24
    assert len(mesh.indices) % 3 == 0
    # First quad (rows 0-1, cols 0-1): deterministic winding.
    assert mesh.indices[:6].tolist() == [0, 3, 1, 3, 4, 1]


def test_flat_4x4_counts() -> None:
    mesh = build_terrain_mesh(flat_dsm(4, 4, 1.0))
    assert mesh.vertex_count == 16
    assert mesh.triangle_count == 18
    assert mesh.coverage == 1.0


def test_2x2_minimal() -> None:
    mesh = build_terrain_mesh(flat_dsm(2, 2, 2.0))
    assert mesh.vertex_count == 4
    assert mesh.triangle_count == 2
    assert mesh.indices.tolist() == [0, 2, 1, 2, 3, 1]


def test_elevation_preserved_exactly() -> None:
    mesh = build_terrain_mesh(flat_dsm(3, 3, 5.0))
    assert bool((mesh.vertices[:, 1] == 5.0).all())


def test_indices_valid() -> None:
    mesh = build_terrain_mesh(flat_dsm(4, 4, 1.0))
    assert bool((mesh.indices >= 0).all())
    assert bool((mesh.indices < mesh.vertex_count).all())


def test_local_planar_coordinates() -> None:
    mesh = build_terrain_mesh(flat_dsm(3, 2, 0.0))
    # Vertex order rows top-to-bottom, cols left-to-right: x = col, z = row.
    assert mesh.vertices[0].tolist() == [0.0, 0.0, 0.0]
    assert mesh.vertices[2].tolist() == [2.0, 0.0, 0.0]
    assert mesh.vertices[3].tolist() == [0.0, 0.0, 1.0]
    assert mesh.vertices[5].tolist() == [2.0, 0.0, 1.0]
