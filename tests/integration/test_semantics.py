"""Finiteness, semantics, georeferencing, frame, mapping, provenance."""

from pathlib import Path

import pytest

from depthwizard.backends.synthetic import SyntheticDepthBackend
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.dsm import rasterize_height_product
from depthwizard.errors import InvalidInputError
from depthwizard.height import create_scientific_height_product
from depthwizard.integration.adapt import (
    depth_to_transport,
    dsm_to_transport,
    mesh_to_transport,
)
from depthwizard.mesh import build_terrain_mesh
from tests.height.support import exact_calibration, geotiff_chain
from tests.integration.support import depth_fixture, dsm_fixture, mesh_fixture


def test_nan_mesh_rejected(tmp_path: Path) -> None:
    mesh = mesh_fixture(tmp_path)
    rotten = mesh.model_copy(update={"vertices": mesh.vertices.copy()})
    rotten.vertices[0, 0] = float("nan")
    with pytest.raises(InvalidInputError, match="finite"):
        mesh_to_transport(rotten)


def test_inf_normal_rejected(tmp_path: Path) -> None:
    mesh = mesh_fixture(tmp_path)
    rotten = mesh.model_copy(update={"normals": mesh.normals.copy()})
    rotten.normals[1, 1] = float("inf")
    with pytest.raises(InvalidInputError, match="finite"):
        mesh_to_transport(rotten)


def test_relative_stays_relative(tmp_path: Path) -> None:
    transport = depth_to_transport(depth_fixture(tmp_path))
    assert transport.depth_scale == "relative"
    assert transport.units is None
    assert transport.elevation_semantics == "relative_depth"


def test_metric_dsm_explicit(tmp_path: Path) -> None:
    from depthwizard.integration.adapt import dsm_to_transport as convert

    transport = convert(dsm_fixture(tmp_path))
    assert transport.units == "meters"
    assert transport.semantics == "height_agl_ndsm"


def test_georeferenced_transport(tmp_path: Path) -> None:
    depth, inspection = geotiff_chain(tmp_path)
    assert inspection.georeferencing.value == "georeferenced_no_elevation_reference"
    result = SyntheticDepthBackend().estimate_depth(inspection)
    calibration = exact_calibration(
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        source_checksum=inspection.handle.sha256,
    )
    product = create_scientific_height_product(
        result, calibration, ElevationSemantics.ABSOLUTE_ELEVATION_DSM
    )
    grid = rasterize_height_product(product)
    transport = dsm_to_transport(grid)
    assert transport.georeferencing == "georeferenced_no_elevation_reference"
    assert transport.spatial.kind == "present"
    details = transport.spatial.details
    assert details is not None
    assert details.crs == "EPSG:32643"
    assert details.transform is not None
    assert (details.transform.a, details.transform.b) == (100.0, 0.5)
    assert details.bounds is not None
    assert (details.bounds.min_x, details.bounds.max_y) == (100.0, 200.0)
    assert transport.semantics == "absolute_elevation_dsm"


def test_nongeoreferenced_absent(tmp_path: Path) -> None:
    transport = dsm_to_transport(dsm_fixture(tmp_path))
    assert transport.spatial.kind == "not_applicable"
    assert transport.spatial.details is None


def test_frame_and_origin(tmp_path: Path) -> None:
    transport = mesh_to_transport(mesh_fixture(tmp_path))
    assert transport.frame == "local"
    assert transport.origin_x is None
    assert transport.origin_y is None


def test_georeferenced_frame_and_origin(tmp_path: Path) -> None:
    depth, inspection = geotiff_chain(tmp_path)
    calibration = exact_calibration(
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        source_checksum=inspection.handle.sha256,
    )
    product = create_scientific_height_product(
        depth, calibration, ElevationSemantics.ABSOLUTE_ELEVATION_DSM
    )
    mesh = build_terrain_mesh(rasterize_height_product(product))
    transport = mesh_to_transport(mesh)
    assert transport.frame == "georeferenced_local"
    assert transport.origin_x == 100.0
    assert transport.origin_y == 200.0
    # world = origin + local reconstructs the source frame.
    assert transport.origin_x is not None and transport.origin_y is not None
    assert transport.vertices[0] + transport.origin_x == pytest.approx(100.25)
    assert transport.vertices[2] + transport.origin_y == pytest.approx(199.75)


def test_source_mapping_preserved(tmp_path: Path) -> None:
    transport = mesh_to_transport(mesh_fixture(tmp_path))
    assert transport.vertex_source_indices == list(range(48))


def test_provenance_chain(tmp_path: Path) -> None:
    depth_transport = depth_to_transport(depth_fixture(tmp_path))
    mesh_transport = mesh_to_transport(mesh_fixture(tmp_path))
    assert depth_transport.provenance is not None
    assert depth_transport.provenance.model_name == "synthetic-depth"
    assert depth_transport.provenance.input_checksum is not None
    assert mesh_transport.provenance is not None
    assert mesh_transport.provenance.calibration_method == "scale_offset"
    assert mesh_transport.depth_model_name == "synthetic-depth"
    assert mesh_transport.source_checksum == depth_transport.provenance.input_checksum
