"""LOD decimation: build_lod_meshes returns correct count and decreasing vertex counts."""

from depthwizard.mesh import TerrainMesh, build_lod_meshes, build_terrain_mesh, decimate_mesh
from tests.mesh.support import flat_dsm


def test_build_lod_meshes_count():
    grid = flat_dsm(8, 8, 1.0)
    meshes = build_lod_meshes(grid, (1, 2, 4))
    assert len(meshes) == 3
    for mesh in meshes:
        assert isinstance(mesh, TerrainMesh)


def test_build_lod_meshes_vertex_counts_decrease():
    grid = flat_dsm(8, 8, 1.0)
    meshes = build_lod_meshes(grid, (1, 2, 4))
    counts = [m.vertex_count for m in meshes]
    assert counts == sorted(counts, reverse=True)
    assert counts[0] > counts[1] > counts[2]


def test_build_lod_meshes_flags():
    grid = flat_dsm(8, 8, 1.0)
    meshes = build_lod_meshes(grid, (1, 2, 4))
    assert meshes[0].decimated is False
    assert meshes[0].lod_level == 1
    assert meshes[1].decimated is True
    assert meshes[1].lod_level == 2
    assert meshes[2].decimated is True
    assert meshes[2].lod_level == 4


def test_build_lod_meshes_single_level():
    grid = flat_dsm(4, 4, 2.0)
    meshes = build_lod_meshes(grid, (2,))
    assert len(meshes) == 1
    assert meshes[0].vertex_count == 4  # 4x4 -> 2x2 -> 4 valid
    assert meshes[0].decimated is True
    assert meshes[0].lod_level == 2


def test_decimate_mesh_reduces_vertices():
    grid = flat_dsm(8, 8, 1.0)
    mesh = build_terrain_mesh(grid)
    decimated = decimate_mesh(mesh, target_ratio=0.5)
    assert decimated.vertex_count < mesh.vertex_count
    assert decimated.decimated is True
    assert decimated.lod_level is None


def test_decimate_mesh_target_vertices():
    grid = flat_dsm(8, 8, 1.0)
    mesh = build_terrain_mesh(grid)
    decimated = decimate_mesh(mesh, target_vertices=10)
    assert decimated.vertex_count <= 10
    assert decimated.decimated is True


def test_decimate_mesh_no_target_returns_original():
    grid = flat_dsm(4, 4, 1.0)
    mesh = build_terrain_mesh(grid)
    result = decimate_mesh(mesh)
    assert result.vertex_count == mesh.vertex_count
    assert result.decimated is False


def test_decimate_mesh_target_above_count_returns_original():
    grid = flat_dsm(4, 4, 1.0)
    mesh = build_terrain_mesh(grid)
    result = decimate_mesh(mesh, target_vertices=mesh.vertex_count + 10)
    assert result.vertex_count == mesh.vertex_count
    assert result.decimated is False


def test_decimate_mesh_valid_topology():
    grid = flat_dsm(6, 6, 1.0)
    mesh = build_terrain_mesh(grid)
    decimated = decimate_mesh(mesh, target_ratio=0.3)
    assert decimated.triangle_count > 0
    assert len(decimated.indices) == 3 * decimated.triangle_count
    assert bool((decimated.indices >= 0).all())
    assert bool((decimated.indices < decimated.vertex_count).all())


def test_decimate_mesh_preserves_metadata():
    grid = flat_dsm(6, 6, 2.0)
    mesh = build_terrain_mesh(grid)
    decimated = decimate_mesh(mesh, target_ratio=0.5)
    assert decimated.units == mesh.units
    assert decimated.semantics == mesh.semantics
    assert decimated.frame == mesh.frame
    assert decimated.width == mesh.width
    assert decimated.height == mesh.height


def test_decimate_mesh_flat_plane():
    grid = flat_dsm(4, 4, 3.0)
    mesh = build_terrain_mesh(grid)
    decimated = decimate_mesh(mesh, target_ratio=0.5)
    assert decimated.vertex_count > 0
    assert decimated.triangle_count > 0
