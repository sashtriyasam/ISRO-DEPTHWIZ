"""Geospatial preservation, provenance chain, source immutability."""

import hashlib
from pathlib import Path

from depthwizard.contracts.semantics import ElevationSemantics, GeoreferencingLevel
from depthwizard.contracts.spatial import SpatialKind
from depthwizard.mesh import CoordinateFrame
from depthwizard.pipeline import PipelineRunner
from depthwizard.version import __version__
from tests.ingestion.fixtures import make_png
from tests.pipeline.support import geotiff_input, make_request, png_input


def test_georeferenced_chain(tmp_path: Path) -> None:
    result = PipelineRunner().run(make_request(geotiff_input(tmp_path), build_mesh=True))
    assert result.succeeded
    assert result.inspection is not None
    assert result.inspection.georeferencing is (
        GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE
    )
    assert result.dsm is not None
    details = result.dsm.spatial.details
    assert details is not None
    assert details.crs == "EPSG:32643"
    assert details.transform is not None
    assert details.transform.as_tuple() == (100.0, 0.5, 0.0, 200.0, 0.0, -0.5)
    assert result.mesh is not None
    assert result.mesh.frame is CoordinateFrame.GEOREFERENCED_LOCAL
    assert result.mesh.origin_x == 100.0
    assert result.mesh.origin_y == 200.0


def test_nongeoreferenced_chain(tmp_path: Path) -> None:
    result = PipelineRunner().run(make_request(png_input(tmp_path), build_mesh=True))
    assert result.succeeded
    assert result.product is not None
    assert result.product.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED
    assert result.dsm is not None
    assert result.dsm.spatial.kind is SpatialKind.NOT_APPLICABLE
    assert result.dsm.spatial.details is None
    assert result.mesh is not None
    assert result.mesh.frame is CoordinateFrame.LOCAL
    assert result.mesh.origin_x is None
    # Only vertical metric semantics; no horizontal CRS claims.
    assert result.product.units == "meters"
    assert result.product.semantics is ElevationSemantics.HEIGHT_AGL_NDSM


def test_provenance_chain(tmp_path: Path) -> None:
    source = make_png(tmp_path / "a.png")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    result = PipelineRunner().run(make_request(str(source)))
    assert result.succeeded
    assert result.input_checksum == digest
    assert result.backend_name == "synthetic-depth"
    assert result.backend_version == "0.1.0"
    assert result.calibration_method == "scale_offset"
    assert result.calibration_reference == "synthetic-test-ref"
    assert result.calibration_scale == 2.5
    assert result.calibration_offset == 10.0
    assert result.target_semantics is ElevationSemantics.HEIGHT_AGL_NDSM
    assert result.mesh_requested is False
    assert result.geotiff_path is None
    assert result.engine_version == __version__
    assert result.product is not None
    assert result.product.provenance.input_checksum == digest
    assert result.dsm is not None
    assert result.dsm.provenance.calibration_method == "scale_offset"


def test_source_immutability(tmp_path: Path) -> None:
    source = make_png(tmp_path / "a.png")
    before = source.read_bytes()
    target = tmp_path / "out.tif"
    request = make_request(str(source), build_mesh=True, geotiff_path=str(target))
    snapshot = repr(request)
    result = PipelineRunner().run(request)
    assert result.succeeded
    assert source.read_bytes() == before
    assert repr(request) == snapshot
    remaining = {child.name for child in tmp_path.iterdir()}
    assert remaining == {"a.png", "out.tif"}
