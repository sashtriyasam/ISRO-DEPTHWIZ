"""Shared builders: rasterized DSM grids from deterministic chains."""

from pathlib import Path

import numpy as np

from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.dsm import DSMGrid, rasterize_height_product
from depthwizard.height import ScientificHeightProduct, create_scientific_height_product
from tests.height.support import exact_calibration, geotiff_chain, png_chain


def agl_grid(tmp_path: Path) -> DSMGrid:
    """Non-georeferenced AGL grid (PNG fixture chain)."""
    depth, inspection = png_chain(tmp_path)
    calibration = exact_calibration(
        ElevationSemantics.HEIGHT_AGL_NDSM,
        source_checksum=inspection.handle.sha256,
    )
    product = create_scientific_height_product(
        depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM
    )
    return rasterize_height_product(product)


def absolute_grid(tmp_path: Path) -> DSMGrid:
    """Georeferenced absolute-elevation grid (GeoTIFF fixture chain)."""
    depth, inspection = geotiff_chain(tmp_path)
    calibration = exact_calibration(
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        source_checksum=inspection.handle.sha256,
    )
    product = create_scientific_height_product(
        depth, calibration, ElevationSemantics.ABSOLUTE_ELEVATION_DSM
    )
    return rasterize_height_product(product)


def agl_product(tmp_path: Path) -> ScientificHeightProduct:
    """Non-georeferenced AGL product (PNG fixture chain)."""
    depth, inspection = png_chain(tmp_path)
    calibration = exact_calibration(
        ElevationSemantics.HEIGHT_AGL_NDSM,
        source_checksum=inspection.handle.sha256,
    )
    return create_scientific_height_product(depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM)


def read_all(path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Read data, mask and profile from a GeoTIFF (test helper)."""
    import warnings

    import rasterio
    from rasterio.errors import NotGeoreferencedWarning

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.open(path) as dataset:
            return dataset.read(1), dataset.read_masks(1), dict(dataset.profile)
