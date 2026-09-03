"""Reusable raster-coordinate mathematics (no science, no I/O).

Sole owner of CRS handling, affine pixel/world conversion, bounds,
overlap, grid compatibility and reprojection/alignment primitives for
future DEM/reference work. Backed by rasterio/GDAL (CRS, warp) and
NumPy; no hand-written projection math, no Shapely, no pyproj.
"""

from depthwizard.geospatial.crs import crs_equal, parse_crs, require_crs
from depthwizard.geospatial.grids import (
    AlignmentStatus,
    CompatibilityResult,
    TargetGrid,
    check_grid_compatibility,
    classify_alignment,
)
from depthwizard.geospatial.overlap import OverlapResult, calculate_overlap
from depthwizard.geospatial.transforms import (
    PixelAnchor,
    from_affine,
    pixel_to_world,
    raster_bounds,
    require_invertible,
    to_affine,
    transform_determinant,
    world_to_pixel,
)
from depthwizard.geospatial.warp import (
    ReprojectedRaster,
    ResamplingMethod,
    align_raster,
    reproject_array,
)

__all__ = [
    "AlignmentStatus",
    "CompatibilityResult",
    "OverlapResult",
    "PixelAnchor",
    "ReprojectedRaster",
    "ResamplingMethod",
    "TargetGrid",
    "align_raster",
    "calculate_overlap",
    "check_grid_compatibility",
    "classify_alignment",
    "crs_equal",
    "from_affine",
    "parse_crs",
    "pixel_to_world",
    "raster_bounds",
    "reproject_array",
    "require_crs",
    "require_invertible",
    "to_affine",
    "transform_determinant",
    "world_to_pixel",
]
