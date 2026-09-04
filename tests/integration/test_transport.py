"""Depth/calibration/DSM/mesh transport mapping (values preserved)."""

from pathlib import Path

from depthwizard.integration.adapt import (
    calibration_to_transport,
    depth_to_transport,
    dsm_to_transport,
    mesh_to_transport,
    terrain_product,
)
from tests.integration.support import (
    calibration_fixture,
    depth_fixture,
    dsm_fixture,
    mesh_fixture,
)


def test_depth_transport(tmp_path: Path) -> None:
    transport = depth_to_transport(depth_fixture(tmp_path))
    assert transport.model_name == "synthetic-depth"
    assert transport.model_version == "0.1.0"
    assert transport.input_resolution.width == 8
    assert transport.output_resolution.height == 6
    assert transport.depth_scale == "relative"
    assert transport.elevation_semantics == "relative_depth"
    assert transport.georeferencing == "non_georeferenced"
    assert len(transport.depth_values) == 48
    assert transport.confidence_values is None
    assert transport.valid_mask is None
    assert transport.units is None
    assert transport.spatial.kind == "not_applicable"
    assert transport.spatial.details is None
    assert transport.preprocessing == {"synthetic_pattern": "separable-sinusoid-normalized"}
    assert transport.provenance is not None
    assert transport.provenance.model_name == "synthetic-depth"


def test_calibration_transport() -> None:
    transport = calibration_to_transport(calibration_fixture())
    assert transport.method == "scale_offset"
    assert (transport.scale, transport.offset) == (2.5, 10.0)
    assert transport.reference_id == "ref-transport"
    assert transport.reference_units == "meters"
    assert transport.target_semantics == "height_agl_ndsm"
    assert (transport.total_samples, transport.valid_samples) == (5, 5)
    assert transport.rmse == 0.0
    assert transport.r_squared == 1.0
    assert transport.engine_version == "0.1.0"


def test_dsm_transport(tmp_path: Path) -> None:
    transport = dsm_to_transport(dsm_fixture(tmp_path))
    assert (transport.width, transport.height) == (8, 6)
    assert transport.dtype == "float32"
    assert transport.units == "meters"
    assert transport.semantics == "height_agl_ndsm"
    assert len(transport.values) == 48
    assert transport.valid_mask == [True] * 48
    assert transport.invalid_count == 0
    assert transport.nodata is None  # NaN has no JSON form
    assert transport.georeferencing == "non_georeferenced"
    assert transport.spatial.kind == "not_applicable"


def test_dsm_null_policy(tmp_path: Path) -> None:
    grid = dsm_fixture(tmp_path)
    poisoned = grid.model_copy(
        update={
            "array": grid.array.copy(),
            "valid_mask": grid.valid_mask.copy(),
            "invalid_count": 1,
        }
    )
    poisoned.array[0, 0] = float("nan")
    poisoned.valid_mask[0, 0] = False
    transport = dsm_to_transport(poisoned)
    assert transport.values[0] is None
    assert transport.valid_mask[0] is False
    assert transport.invalid_count == 1
    assert transport.values[1] is not None


def test_mesh_transport(tmp_path: Path) -> None:
    transport = mesh_to_transport(mesh_fixture(tmp_path))
    assert transport.vertex_count == 48
    assert transport.triangle_count == 70
    assert len(transport.vertices) == 3 * 48
    assert len(transport.normals) == 3 * 48
    assert len(transport.uvs) == 2 * 48
    assert len(transport.indices) == 3 * 70
    assert len(transport.vertex_source_indices) == 48
    assert transport.frame == "local"
    assert transport.origin_x is None
    assert transport.origin_y is None
    assert (transport.width, transport.height) == (8, 6)
    assert transport.units == "meters"
    assert transport.semantics == "height_agl_ndsm"
    assert transport.georeferencing == "non_georeferenced"
    assert transport.depth_model_name == "synthetic-depth"
    assert transport.calibration_method == "scale_offset"
    assert transport.calibration_reference is not None
    assert (transport.calibration_scale, transport.calibration_offset) == (2.5, 10.0)
    assert 0.0 <= transport.coverage <= 1.0
    assert transport.provenance is not None


def test_terrain_product_shape(tmp_path: Path) -> None:
    product = terrain_product(
        depth_fixture(tmp_path), dsm_fixture(tmp_path), mesh_fixture(tmp_path)
    )
    assert product.kind == "terrain"
    assert product.dsm.width == 8
    assert product.mesh.vertex_count == 48
    assert product.depth_result.model_name == "synthetic-depth"
