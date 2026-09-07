"""LOD decimation: build_lod_meshes returns correct count and decreasing vertex counts."""

from depthwizard.mesh import TerrainMesh, build_lod_meshes
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
