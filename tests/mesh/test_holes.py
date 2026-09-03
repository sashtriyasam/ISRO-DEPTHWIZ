"""Nodata holes: conservative omission, never bridged, explicit failures."""

import pytest

from depthwizard.errors import MeshGenerationError
from depthwizard.mesh import TerrainMesh, build_terrain_mesh
from tests.mesh.support import flat_dsm, holed_dsm


def _referenced_sources(mesh: TerrainMesh) -> set[int]:
    return set(mesh.vertex_source_indices[mesh.indices].tolist())


def test_single_hole_omits_touching_quads() -> None:
    mesh = build_terrain_mesh(holed_dsm(4, 4, 1.0, {(1, 1)}))
    assert mesh.vertex_count == 15
    assert mesh.valid_source_pixels == 15
    assert mesh.invalid_source_pixels == 1
    # 9 quads total, 4 touch pixel (1,1) -> 5 quads -> 10 triangles.
    assert mesh.triangle_count == 10
    assert mesh.skipped_cells == 4
    assert mesh.coverage == pytest.approx(10 / 18)
    assert 1 * 4 + 1 not in _referenced_sources(mesh)


def test_full_row_hole() -> None:
    invalid = {(1, c) for c in range(4)}
    mesh = build_terrain_mesh(holed_dsm(4, 4, 1.0, invalid))
    assert mesh.vertex_count == 12
    # Only the bottom strip (rows 2-3) triangulates: 3 quads -> 6 tris.
    assert mesh.triangle_count == 6
    assert mesh.skipped_cells == 6
    assert mesh.coverage == pytest.approx(6 / 18)
    assert not ({1 * 4 + c for c in range(4)} & _referenced_sources(mesh))


def test_corner_hole() -> None:
    mesh = build_terrain_mesh(holed_dsm(4, 4, 1.0, {(0, 0)}))
    assert mesh.vertex_count == 15
    assert mesh.triangle_count == 16
    assert mesh.skipped_cells == 1
    assert 0 not in _referenced_sources(mesh)


def test_disconnected_holes() -> None:
    mesh = build_terrain_mesh(holed_dsm(4, 4, 1.0, {(0, 0), (3, 3)}))
    assert mesh.vertex_count == 14
    assert mesh.triangle_count == 14
    assert mesh.skipped_cells == 2
    assert not ({0, 15} & _referenced_sources(mesh))


def test_center_hole_kills_all_quads() -> None:
    # Pixel (1,1) of a 3x3 participates in all 4 quads: with the
    # conservative all-corners-valid policy no triangle can form.
    with pytest.raises(MeshGenerationError, match="no usable quad topology"):
        build_terrain_mesh(holed_dsm(3, 3, 1.0, {(1, 1)}))


def test_sparse_valid_pixels_fail() -> None:
    with pytest.raises(MeshGenerationError, match="no usable quad topology"):
        build_terrain_mesh(
            holed_dsm(3, 3, 1.0, {(0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (2, 0), (2, 1)})
        )


def test_degenerate_dimensions_fail() -> None:
    with pytest.raises(MeshGenerationError, match="2x2"):
        build_terrain_mesh(flat_dsm(1, 1, 1.0))
    with pytest.raises(MeshGenerationError, match="2x2"):
        build_terrain_mesh(flat_dsm(1, 4, 1.0))
    with pytest.raises(MeshGenerationError, match="2x2"):
        build_terrain_mesh(flat_dsm(4, 1, 1.0))


def test_all_invalid_fails() -> None:
    grid = holed_dsm(2, 2, 1.0, {(0, 0), (0, 1), (1, 0), (1, 1)})
    with pytest.raises(MeshGenerationError, match="0 valid"):
        build_terrain_mesh(grid)


def test_rejects_non_grid() -> None:
    with pytest.raises(TypeError, match="DSMGrid"):
        build_terrain_mesh("not-a-grid")  # type: ignore[arg-type]
