"""Scientific slope analysis on calibrated metric DSM grids.

Slope is derived analysis, never a modified elevation product: the
source ``DSMGrid`` is untouched and slope values live in a dedicated
``SlopeGrid`` with degrees as explicit units.

Horizontal metric honesty is enforced up front.  Slope needs a real
planimetric metre: the source grid must carry ``PRESENT`` spatial
context with a known positive ``resolution_gsd`` and planimetric
``units == 'meters'``.  Geographic-degree grids (or any unknown
horizontal units) are refused with an explicit error — never a fake
metre conversion, never degrees-as-metres.

Numerics are deliberately conservative: central differences on
interior pixels whose full 3×3 neighbourhood is valid; borders and
any pixel touching nodata are invalid (no extrapolation, no hole
bridging).  Output is deterministic for identical inputs.
"""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.contracts.artifacts import METRIC_UNIT
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import ElevationSemantics, GeoreferencingLevel
from depthwizard.contracts.spatial import SpatialContext, SpatialDetails, SpatialKind
from depthwizard.dsm.grid import DSMGrid
from depthwizard.errors import GeospatialProcessingError, InvalidInputError
from depthwizard.geospatial.crs import crs_is_projected_metric, parse_crs

#: Slope output units: degrees on [0, 90).
SLOPE_UNIT = "degrees"


class SlopeGrid(BaseModel):
    """Owned 2D raster of terrain slope in degrees with validity mask."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    array: np.ndarray = Field(description="2D float array of slope degrees, shape (height, width).")
    valid_mask: np.ndarray = Field(
        description="2D bool array, True marks scientifically valid slope pixels."
    )
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    dtype: str = Field(description="Storage dtype name ('float32'/'float64').")
    units: str = Field(description="Always explicit slope units ('degrees').")
    derived_from_semantics: ElevationSemantics = Field(
        description="Meaning of the source elevation product (unchanged)."
    )
    invalid_count: int = Field(ge=0, description="Pixels masked as invalid.")
    georeferencing: GeoreferencingLevel = Field(description="Preserved, never upgraded.")
    spatial: SpatialContext = Field(description="Preserved source spatial context.")
    depth_model_name: str = Field(min_length=1)
    depth_model_version: str | None = None
    depth_checkpoint_id: str | None = None
    source_input_id: str | None = None
    source_checksum: str | None = None
    calibration_method: str = Field(min_length=1)
    calibration_reference: str = Field(min_length=1)
    calibration_scale: float
    calibration_offset: float
    calibration_valid_samples: int = Field(ge=0)
    provenance: ProductProvenance = Field(description="Reused source provenance.")

    @model_validator(mode="after")
    def _check_slope_honesty(self) -> SlopeGrid:
        if self.units != SLOPE_UNIT:
            raise ValueError(f"slope grid requires explicit units ('{SLOPE_UNIT}')")
        if not isinstance(self.array, np.ndarray) or self.array.ndim != 2:
            raise ValueError("slope array must be an explicit 2D array")
        if self.array.dtype.kind != "f" or str(self.array.dtype) not in (
            "float32",
            "float64",
        ):
            raise ValueError("slope array must be float32/float64")
        if self.array.shape != (self.height, self.width):
            raise ValueError(
                f"array shape {self.array.shape} != (height, width) ({self.height}, {self.width})"
            )
        if self.dtype != str(self.array.dtype):
            raise ValueError("dtype label must match the array dtype")
        if (
            not isinstance(self.valid_mask, np.ndarray)
            or self.valid_mask.dtype.kind != "b"
            or self.valid_mask.shape != self.array.shape
        ):
            raise ValueError("valid_mask must be a bool array matching the grid shape")
        if self.invalid_count != int((~self.valid_mask).sum()):
            raise ValueError("invalid_count must equal the masked pixel count")
        valid_cells = self.array[self.valid_mask]
        if valid_cells.size and (
            not bool(np.isfinite(valid_cells).all())
            or bool((valid_cells < 0.0).any())
            or bool((valid_cells >= 90.0).any())
        ):
            raise ValueError("valid slope pixels must be finite values in [0, 90)")
        if self.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED:
            if self.spatial.kind is SpatialKind.PRESENT:
                raise ValueError("NON_GEOREFERENCED grid must not carry PRESENT details")
        return self


def _planimetric_metre_step(grid: DSMGrid) -> tuple[float, float]:
    """Resolve the (column, row) pixel steps in metres, or refuse honestly.

    Steps are the ground distances between neighbouring pixel centres:
    ``hypot(b, e)`` along columns and ``hypot(c, f)`` along rows of the
    stored GDAL-order affine, so non-square and rotated pixels are handled. Without a
    transform the recorded square ``resolution_gsd`` is used for both.

    Metric horizontal units come from the recorded planimetric
    ``units`` when explicit, else from introspecting the authoritative
    CRS identifier (projected CRS with metre linear units, via
    rasterio — no invented mappings, no hardcoded EPSG lists).
    Geographic-degree grids and unknown CRS are refused, never
    silently converted.
    """
    if grid.units != METRIC_UNIT:
        raise InvalidInputError(
            f"slope requires a metric DSM grid ('{METRIC_UNIT}'); got '{grid.units}'"
        )
    if grid.spatial.kind is not SpatialKind.PRESENT or grid.spatial.details is None:
        raise InvalidInputError("slope requires PRESENT spatial context with resolution")
    details = grid.spatial.details
    steps = _pixel_steps(details)
    if details.units == METRIC_UNIT:
        return steps
    if details.units is not None:
        raise InvalidInputError(
            "slope requires metric planimetric units ('meters'); "
            f"got {details.units!r} — geographic-degree grids are refused, "
            "never silently converted"
        )
    if details.crs is None:
        raise InvalidInputError(
            "slope requires metric planimetric units: no units recorded and no CRS to introspect"
        )
    try:
        parse_crs(details.crs)
    except GeospatialProcessingError as e:
        raise InvalidInputError(
            f"slope cannot interpret CRS {details.crs!r} for planimetric units: {e}"
        ) from e
    if not crs_is_projected_metric(details.crs):
        raise InvalidInputError(
            f"slope requires a projected metric CRS; got crs={details.crs!r} — "
            "geographic-degree grids are refused, never silently converted"
        )
    return steps


def _pixel_steps(details: SpatialDetails) -> tuple[float, float]:
    """Ground spacing between adjacent pixel centres (column step, row step)."""
    transform = details.transform
    if transform is not None:
        col_step = math.hypot(float(transform.b), float(transform.e))
        row_step = math.hypot(float(transform.c), float(transform.f))
    else:
        gsd = details.resolution_gsd
        if gsd is None or not math.isfinite(gsd):
            raise InvalidInputError("slope requires a transform or a known finite resolution_gsd")
        col_step = row_step = float(gsd)
    for step in (col_step, row_step):
        if not math.isfinite(step) or step <= 0.0:
            raise InvalidInputError("slope requires positive finite pixel spacing")
    return col_step, row_step


def compute_slope(grid: DSMGrid) -> SlopeGrid:
    """Derive slope-in-degrees analysis from a metric DSM grid.

    Central differences on interior pixels with a fully valid 3×3
    neighbourhood; borders and nodata-adjacent pixels are invalid.
    The source grid is never mutated.  Deterministic for identical
    inputs.
    """
    if not isinstance(grid, DSMGrid):
        raise InvalidInputError(f"compute_slope requires a DSMGrid, got {type(grid).__name__}")
    col_step, row_step = _planimetric_metre_step(grid)

    elevation = np.asarray(grid.array, dtype=np.float64)
    valid = np.asarray(grid.valid_mask, dtype=bool)
    height, width = elevation.shape

    slope = np.full((height, width), np.nan, dtype=np.float64)
    out_valid = np.zeros((height, width), dtype=bool)
    if height >= 3 and width >= 3:
        neighbourhood_valid = (
            valid[:-2, :-2]
            & valid[:-2, 1:-1]
            & valid[:-2, 2:]
            & valid[1:-1, :-2]
            & valid[1:-1, 1:-1]
            & valid[1:-1, 2:]
            & valid[2:, :-2]
            & valid[2:, 1:-1]
            & valid[2:, 2:]
        )
        dz_dcol = (elevation[1:-1, 2:] - elevation[1:-1, :-2]) / (2.0 * col_step)
        dz_drow = (elevation[2:, 1:-1] - elevation[:-2, 1:-1]) / (2.0 * row_step)
        magnitude = np.hypot(dz_dcol, dz_drow)
        interior = np.degrees(np.arctan(magnitude))
        slope[1:-1, 1:-1][neighbourhood_valid] = interior[neighbourhood_valid]
        out_valid[1:-1, 1:-1] = neighbourhood_valid

    finite = np.isfinite(slope)
    if bool((out_valid & ~finite).any()):
        raise InvalidInputError("slope computation produced non-finite valid pixels")
    out_valid = out_valid & finite

    return SlopeGrid(
        array=slope.astype(np.float64),
        valid_mask=out_valid,
        width=width,
        height=height,
        dtype="float64",
        units=SLOPE_UNIT,
        derived_from_semantics=grid.semantics,
        invalid_count=int((~out_valid).sum()),
        georeferencing=grid.georeferencing,
        spatial=grid.spatial,
        depth_model_name=grid.depth_model_name,
        depth_model_version=grid.depth_model_version,
        depth_checkpoint_id=grid.depth_checkpoint_id,
        source_input_id=grid.source_input_id,
        source_checksum=grid.source_checksum,
        calibration_method=grid.calibration_method,
        calibration_reference=grid.calibration_reference,
        calibration_scale=grid.calibration_scale,
        calibration_offset=grid.calibration_offset,
        calibration_valid_samples=grid.calibration_valid_samples,
        provenance=grid.provenance,
    )
