"""Deterministic control fixtures (direct contracts + fixture chains)."""

from typing import Any

import numpy as np

from depthwizard.contracts.artifacts import DepthResult, ImageResolution
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import (
    DepthScale,
    ElevationSemantics,
    GeoreferencingLevel,
)
from depthwizard.contracts.spatial import (
    AffineTransform,
    Bounds,
    SpatialContext,
    SpatialDetails,
    SpatialKind,
)
from depthwizard.controls.models import CoordinateSpace, SurfaceElevationControl
from depthwizard.dem.models import TerrainReferenceGrid

FLAT_TRANSFORM = AffineTransform(a=0.0, b=1.0, c=0.0, d=0.0, e=0.0, f=1.0)
FLAT_CRS = "EPSG:32643"
CHECKSUM = "a" * 64


def relative_depth(
    predicted: tuple[float, ...] = (0.1, 0.4, 0.8),
    *,
    georeferenced: bool = False,
    valid_mask: tuple[bool, ...] | None = None,
) -> DepthResult:
    """Direct 3x1 (or Nx1) RELATIVE DepthResult for unit tests."""
    width, height = len(predicted), 1
    resolution = ImageResolution(width=width, height=height)
    if georeferenced:
        georeferencing = GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE
        spatial = SpatialContext(
            kind=SpatialKind.PRESENT,
            details=SpatialDetails(
                crs=FLAT_CRS,
                transform=FLAT_TRANSFORM,
                bounds=Bounds(min_x=0.0, min_y=0.0, max_x=float(width), max_y=1.0),
                raster_width=width,
                raster_height=height,
                source="test",
            ),
        )
    else:
        georeferencing = GeoreferencingLevel.NON_GEOREFERENCED
        spatial = SpatialContext(kind=SpatialKind.NOT_APPLICABLE)
    return DepthResult(
        model_name="test-backend",
        input_resolution=resolution,
        output_resolution=resolution,
        depth_scale=DepthScale.RELATIVE,
        elevation_semantics=ElevationSemantics.RELATIVE_DEPTH,
        georeferencing=georeferencing,
        depth_values=tuple(predicted),
        valid_mask=valid_mask,
        spatial=spatial,
    )


def terrain_grid(
    values: tuple[float, ...] = (100.0, 105.0, 110.0),
    invalid: frozenset[int] | None = None,
) -> TerrainReferenceGrid:
    """Direct 3x1 terrain grid in the flat test frame."""
    width, height = len(values), 1
    array = np.array(values, dtype=np.float64).reshape(height, width)
    mask = np.isfinite(array)
    if invalid:
        for index in invalid:
            mask.ravel()[index] = False
    clean = np.where(mask, array, np.nan)
    return TerrainReferenceGrid(
        array=np.ascontiguousarray(clean),
        valid_mask=mask,
        width=width,
        height=height,
        dtype="float64",
        units="meters",
        semantics=ElevationSemantics.TERRAIN_ELEVATION,
        nodata=float("nan"),
        invalid_count=int((~mask).sum()),
        crs=FLAT_CRS,
        transform=FLAT_TRANSFORM,
        bounds=Bounds(min_x=0.0, min_y=0.0, max_x=float(width), max_y=1.0),
        resolution=1.0,
        source_dem_id="dem-test",
        source_checksum=CHECKSUM,
        source_crs=FLAT_CRS,
        source_resolution=1.0,
        target_resolution=1.0,
        resampling=None,
        provenance=ProductProvenance(),
    )


def surface(
    control_id: str,
    elevation: float,
    *,
    row: int | None = None,
    col: int | None = None,
    x: float | None = None,
    y: float | None = None,
    crs: str | None = None,
    source_id: str = "survey-1",
    units: str = "meters",
) -> SurfaceElevationControl:
    """Surface control in pixel space (row/col) or world space (x/y)."""
    space = CoordinateSpace.PIXEL if x is None and y is None else CoordinateSpace.WORLD
    kwargs: dict[str, Any] = {
        "control_id": control_id,
        "coordinate_space": space,
        "surface_elevation_m": elevation,
        "units": units,
        "source_id": source_id,
    }
    if row is not None or col is not None:
        kwargs["row"] = row
        kwargs["col"] = col
    if x is not None or y is not None:
        kwargs["x"] = x
        kwargs["y"] = y
    if crs is not None:
        kwargs["crs"] = crs
    return SurfaceElevationControl(**kwargs)
