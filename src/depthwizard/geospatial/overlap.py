"""Rectangular raster-overlap validation (same-frame geometry only).

Bounds from different coordinate systems are never compared raw: when
the CRS identifiers differ structurally, the second bounds are
explicitly transformed into the first frame (densified edges) before
intersection. Missing CRS on either side fails with MissingCRSError —
placement in a common frame is impossible without it. Edge-touching
(zero-area contact) does not count as intersection: DEM work needs
shared pixels, not shared edges.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from depthwizard.contracts.spatial import Bounds
from depthwizard.errors import MissingCRSError
from depthwizard.geospatial.crs import crs_equal


class OverlapResult(BaseModel):
    """Typed overlap outcome (geometry facts, never confidence claims)."""

    model_config = ConfigDict(frozen=True)

    intersects: bool
    bounds: Bounds | None = Field(
        default=None, description="Overlap bounds in the reported CRS frame."
    )
    crs: str | None = Field(default=None, description="CRS identifier of the overlap frame.")
    area: float = Field(ge=0.0, description="Overlap area in frame units.")
    fraction_of_first: float = Field(
        ge=0.0, le=1.0, description="Geometric share of the first raster's area."
    )
    fraction_of_second: float = Field(
        ge=0.0, le=1.0, description="Geometric share of the second raster's area."
    )


def _area(bounds: Bounds) -> float:
    """Non-negative axis-aligned area (degenerate boxes yield 0)."""
    return max(0.0, bounds.max_x - bounds.min_x) * max(0.0, bounds.max_y - bounds.min_y)


def _intersect(first: Bounds, second: Bounds) -> Bounds | None:
    """Positive-area intersection, or None (edge-touching excluded)."""
    left = max(first.min_x, second.min_x)
    bottom = max(first.min_y, second.min_y)
    right = min(first.max_x, second.max_x)
    top = min(first.max_y, second.max_y)
    if right <= left or top <= bottom:
        return None
    return Bounds(min_x=left, min_y=bottom, max_x=right, max_y=top)


def calculate_overlap(
    first_bounds: Bounds,
    first_crs: str | None,
    second_bounds: Bounds,
    second_crs: str | None,
) -> OverlapResult:
    """Validate overlap of two raster footprints with CRS safety.

    Same structured CRS: direct intersection. Different CRS: the second
    bounds are transformed into the first frame first (reported frame
    is always the first CRS). Either CRS missing: MissingCRSError.
    """
    if first_crs is None or second_crs is None:
        raise MissingCRSError(
            "overlap validation requires a CRS on both rasters "
            f"(got {first_crs!r} and {second_crs!r})"
        )
    frame_crs = first_crs
    second_in_frame = second_bounds
    if not crs_equal(first_crs, second_crs):
        from rasterio.warp import transform_bounds

        left, bottom, right, top = transform_bounds(
            second_crs,
            first_crs,
            second_bounds.min_x,
            second_bounds.min_y,
            second_bounds.max_x,
            second_bounds.max_y,
        )
        second_in_frame = Bounds(min_x=left, min_y=bottom, max_x=right, max_y=top)
    overlap = _intersect(first_bounds, second_in_frame)
    if overlap is None:
        return OverlapResult(
            intersects=False,
            bounds=None,
            crs=frame_crs,
            area=0.0,
            fraction_of_first=0.0,
            fraction_of_second=0.0,
        )
    area = _area(overlap)
    first_area = _area(first_bounds)
    second_area = _area(second_in_frame)
    return OverlapResult(
        intersects=True,
        bounds=overlap,
        crs=frame_crs,
        area=area,
        fraction_of_first=area / first_area if first_area > 0.0 else 0.0,
        fraction_of_second=area / second_area if second_area > 0.0 else 0.0,
    )
