"""Spatial preservation: nothing invented, nothing upgraded."""

from pathlib import Path

from depthwizard.contracts.semantics import ElevationSemantics, GeoreferencingLevel
from depthwizard.contracts.spatial import SpatialKind
from depthwizard.height import create_scientific_height_product
from tests.height.support import exact_calibration, geotiff_chain, png_chain


def test_nongeoreferenced_stays_nongeoreferenced(tmp_path: Path) -> None:
    depth, _ = png_chain(tmp_path)
    calibration = exact_calibration(ElevationSemantics.HEIGHT_AGL_NDSM)
    product = create_scientific_height_product(
        depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM
    )
    assert product.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED
    assert product.spatial.kind is SpatialKind.NOT_APPLICABLE
    assert product.spatial.details is None


def test_georeferenced_spatial_preserved(tmp_path: Path) -> None:
    depth, inspection = geotiff_chain(tmp_path)
    calibration = exact_calibration(
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        source_checksum=inspection.handle.sha256,
    )
    product = create_scientific_height_product(
        depth, calibration, ElevationSemantics.ABSOLUTE_ELEVATION_DSM
    )
    assert product.georeferencing is GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE
    assert product.spatial == inspection.spatial
    assert product.spatial == depth.spatial
    details = product.spatial.details
    assert details is not None
    assert details.crs == "EPSG:32643"
    assert details.transform is not None
    assert details.transform.as_tuple() == (100.0, 0.5, 0.0, 200.0, 0.0, -0.5)
    assert (product.width, product.height) == (5, 4)
