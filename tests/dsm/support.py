"""Shared builders: full chains down to ScientificHeightProduct."""

from pathlib import Path

from depthwizard.calibration import CalibrationResult
from depthwizard.contracts.artifacts import DepthResult
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.height import ScientificHeightProduct, create_scientific_height_product
from tests.height.support import exact_calibration, geotiff_chain, png_chain


def agl_png_product(
    tmp_path: Path,
) -> tuple[ScientificHeightProduct, DepthResult, CalibrationResult]:
    """AGL product from the non-georeferenced PNG fixture chain."""
    depth, inspection = png_chain(tmp_path)
    calibration = exact_calibration(
        ElevationSemantics.HEIGHT_AGL_NDSM,
        source_checksum=inspection.handle.sha256,
    )
    product = create_scientific_height_product(
        depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM
    )
    return product, depth, calibration


def absolute_geotiff_product(
    tmp_path: Path,
) -> tuple[ScientificHeightProduct, DepthResult, CalibrationResult]:
    """Absolute-elevation product from the CRS-bearing GeoTIFF chain."""
    depth, inspection = geotiff_chain(tmp_path)
    calibration = exact_calibration(
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        source_checksum=inspection.handle.sha256,
    )
    product = create_scientific_height_product(
        depth, calibration, ElevationSemantics.ABSOLUTE_ELEVATION_DSM
    )
    return product, depth, calibration
