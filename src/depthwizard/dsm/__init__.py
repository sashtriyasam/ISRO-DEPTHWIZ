"""In-memory DSM raster engine (representation, not reinterpretation).

Converts ``ScientificHeightProduct`` to an explicit ``DSMGrid`` 2D
array plus future-writer ``DSMProfile`` metadata. No resampling, no
reprojection, no file writing.
"""

from depthwizard.dsm.grid import (
    BAND_COUNT,
    NODATA,
    DSMGrid,
    DSMProfile,
    RasterizeOptions,
    ResamplingPolicy,
)
from depthwizard.dsm.rasterize import rasterize_height_product
from depthwizard.dsm.slope import SLOPE_UNIT, SlopeGrid, compute_slope

__all__ = [
    "BAND_COUNT",
    "NODATA",
    "DSMGrid",
    "DSMProfile",
    "RasterizeOptions",
    "ResamplingPolicy",
    "SLOPE_UNIT",
    "SlopeGrid",
    "compute_slope",
    "rasterize_height_product",
]
