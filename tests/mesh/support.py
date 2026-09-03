"""Tiny deterministic DSM grids for mesh tests (in-memory only)."""

import numpy as np

from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import ElevationSemantics, GeoreferencingLevel
from depthwizard.contracts.spatial import (
    AffineTransform,
    Bounds,
    SpatialContext,
    SpatialDetails,
    SpatialKind,
)
from depthwizard.dsm import DSMGrid

GEO_CRS = "EPSG:32643"
GEO_AFFINE = (100.0, 0.5, 0.0, 200.0, 0.0, -0.5)


def _georef_spatial(width: int, height: int) -> SpatialContext:
    a, pixel_w, _, d, _, pixel_h = GEO_AFFINE
    return SpatialContext(
        kind=SpatialKind.PRESENT,
        details=SpatialDetails(
            crs=GEO_CRS,
            transform=AffineTransform(a=a, b=pixel_w, c=0.0, d=d, e=0.0, f=pixel_h),
            bounds=Bounds(
                min_x=a,
                min_y=d + pixel_h * height,
                max_x=a + pixel_w * width,
                max_y=d,
            ),
            resolution_gsd=abs(pixel_w),
            nodata=float("nan"),
            raster_width=width,
            raster_height=height,
            source="test",
        ),
    )


def flat_dsm(
    width: int,
    height: int,
    value: float,
    semantics: ElevationSemantics = ElevationSemantics.HEIGHT_AGL_NDSM,
    georef: bool = False,
) -> DSMGrid:
    """Uniform grid where every pixel is valid."""
    return holed_dsm(width, height, value, set(), semantics, georef)


def holed_dsm(
    width: int,
    height: int,
    value: float,
    invalid: set[tuple[int, int]],
    semantics: ElevationSemantics = ElevationSemantics.HEIGHT_AGL_NDSM,
    georef: bool = False,
) -> DSMGrid:
    """Uniform grid with the given (row, col) pixels marked invalid."""
    array = np.full((height, width), value, dtype=np.float64)
    mask = np.ones((height, width), dtype=bool)
    for row, col in invalid:
        mask[row, col] = False
        array[row, col] = float("nan")
    if georef:
        georeferencing = GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE
        spatial = _georef_spatial(width, height)
    else:
        georeferencing = GeoreferencingLevel.NON_GEOREFERENCED
        spatial = SpatialContext(kind=SpatialKind.NOT_APPLICABLE)
    return DSMGrid(
        array=array,
        valid_mask=mask,
        width=width,
        height=height,
        dtype="float64",
        units="meters",
        semantics=semantics,
        nodata=float("nan"),
        invalid_count=len(invalid),
        georeferencing=georeferencing,
        spatial=spatial,
        depth_model_name="test-backend",
        calibration_method="scale_offset",
        calibration_reference="ref-test",
        calibration_scale=1.0,
        calibration_offset=0.0,
        calibration_valid_samples=width * height - len(invalid),
        provenance=ProductProvenance(),
    )


def slope_dsm(width: int, height: int) -> DSMGrid:
    """Planar slope y = 2x + z (local frame) for normal-orientation tests."""
    grid = flat_dsm(width, height, 0.0)
    array = grid.array.copy()
    for row in range(height):
        for col in range(width):
            array[row, col] = 2.0 * col + 1.0 * row
    return grid.model_copy(update={"array": array})
