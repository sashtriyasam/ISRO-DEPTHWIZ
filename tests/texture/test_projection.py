"""RGB texture projection: mapping honesty, dimension agreement, immutability."""

from __future__ import annotations

import numpy as np
import pytest

from depthwizard.errors import InvalidInputError
from depthwizard.mesh import TerrainMesh, build_terrain_mesh
from depthwizard.texture import (
    ColourInterpretation,
    TextureProjection,
    project_texture,
)
from tests.mesh.support import flat_dsm


def _mesh(georef: bool = False) -> TerrainMesh:
    """Small deterministic terrain mesh (5×4 source grid)."""
    return build_terrain_mesh(flat_dsm(5, 4, 10.0, georef=georef))


def test_happy_path_records_mapping() -> None:
    """Matching image/mesh dimensions produce a validated projection."""
    mesh = _mesh()
    projection = project_texture(
        mesh,
        source_input_id="tile.png",
        image_width=5,
        image_height=4,
        colour=ColourInterpretation.RGB_UINT8,
        source_checksum="abc123",
    )
    assert isinstance(projection, TextureProjection)
    assert projection.source_input_id == "tile.png"
    assert projection.source_checksum == "abc123"
    assert (projection.image_width, projection.image_height) == (5, 4)
    assert (projection.mesh_width, projection.mesh_height) == (5, 4)
    assert projection.colour is ColourInterpretation.RGB_UINT8
    assert projection.uv_coverage == pytest.approx(1.0)
    assert projection.georeferencing == mesh.georeferencing
    assert projection.depth_model_name == mesh.depth_model_name


def test_dimension_mismatch_refused() -> None:
    """Image dimensions must equal the mesh source raster dimensions."""
    mesh = _mesh()
    with pytest.raises(ValueError, match="must match"):
        project_texture(
            mesh,
            source_input_id="tile.png",
            image_width=8,
            image_height=6,
            colour=ColourInterpretation.RGB_UINT8,
        )


def test_georeferencing_preserved() -> None:
    """Georeferenced meshes carry their spatial context into the mapping."""
    mesh = _mesh(georef=True)
    projection = project_texture(
        mesh,
        source_input_id="scene.tif",
        image_width=5,
        image_height=4,
        colour=ColourInterpretation.RGB_UINT8,
    )
    assert projection.spatial.kind == mesh.spatial.kind
    assert projection.georeferencing == mesh.georeferencing


def test_rejects_non_mesh() -> None:
    """Non-mesh inputs fail with InvalidInputError."""
    with pytest.raises(InvalidInputError):
        project_texture(
            None,  # type: ignore[arg-type]
            source_input_id="tile.png",
            image_width=5,
            image_height=4,
            colour=ColourInterpretation.RGB_UINT8,
        )


def test_rejects_blank_source_id() -> None:
    """Blank source identity is refused."""
    mesh = _mesh()
    with pytest.raises(InvalidInputError, match="source_input_id"):
        project_texture(
            mesh,
            source_input_id="  ",
            image_width=5,
            image_height=4,
            colour=ColourInterpretation.RGB_UINT8,
        )


def test_rejects_undeclared_colour() -> None:
    """Colour interpretation is declared, never inferred."""
    mesh = _mesh()
    with pytest.raises(InvalidInputError, match="colour"):
        project_texture(
            mesh,
            source_input_id="tile.png",
            image_width=5,
            image_height=4,
            colour="bgr",  # type: ignore[arg-type]
        )


def test_mesh_scientific_coordinates_untouched() -> None:
    """Projection never alters mesh vertices, normals, UVs or indices."""
    mesh = _mesh(georef=True)
    vertices = mesh.vertices.copy()
    normals = mesh.normals.copy()
    uvs = mesh.uvs.copy()
    indices = mesh.indices.copy()
    project_texture(
        mesh,
        source_input_id="scene.tif",
        image_width=5,
        image_height=4,
        colour=ColourInterpretation.RGB_UINT8,
    )
    assert bool(np.array_equal(mesh.vertices, vertices))
    assert bool(np.array_equal(mesh.normals, normals))
    assert bool(np.array_equal(mesh.uvs, uvs))
    assert bool(np.array_equal(mesh.indices, indices))


def test_deterministic() -> None:
    """Repeat projection is identical."""
    mesh = _mesh()
    kwargs = {
        "source_input_id": "tile.png",
        "image_width": 5,
        "image_height": 4,
        "colour": ColourInterpretation.RGB_UINT8,
    }
    assert project_texture(mesh, **kwargs) == project_texture(mesh, **kwargs)  # type: ignore[arg-type]
