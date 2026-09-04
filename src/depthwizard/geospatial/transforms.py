"""Affine pixel/world conversions and raster bounds (contract-based).

The foundation ``AffineTransform`` stores GDAL-order parameters
(x = a + b*col + c*row, y = d + e*col + f*row). Conversions go through
the trustworthy ``Affine`` inverse (``~`` operator) — no hand-written
matrix inversion. Bounds come from Rasterio's transform-aware
``array_bounds`` over the four cell corners (no axis assumptions).
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Any

from depthwizard.contracts.spatial import AffineTransform, Bounds
from depthwizard.errors import GeospatialProcessingError


class PixelAnchor(str, Enum):
    """Reference point within a raster cell (kept distinct on purpose)."""

    CENTER = "center"
    CORNER = "corner"


def check_transform_finite(transform: AffineTransform) -> None:
    """Reject non-finite affine parameters (no fake identity recovery)."""
    values = (
        transform.a,
        transform.b,
        transform.c,
        transform.d,
        transform.e,
        transform.f,
    )
    if not all(math.isfinite(v) for v in values):
        raise GeospatialProcessingError(
            f"affine transform must be finite, got {transform.as_tuple()!r}"
        )


def transform_determinant(transform: AffineTransform) -> float:
    """Planar Jacobian determinant (b*f - c*e) of the GDAL-order affine."""
    check_transform_finite(transform)
    return transform.b * transform.f - transform.c * transform.e


def require_invertible(transform: AffineTransform) -> None:
    """Reject singular transforms before inverse mapping is attempted."""
    if transform_determinant(transform) == 0.0:
        raise GeospatialProcessingError(
            "affine transform is singular (zero determinant); world-to-pixel mapping is undefined"
        )


def to_affine(transform: AffineTransform) -> Any:
    """Convert the contract transform to a rasterio ``Affine``.

    Contract (x = a + b*col + c*row) maps to Affine(a=b, b=c, c=a,
    d=e, e=f, f=d) in rasterio's (col, row) convention. ``Any`` because
    rasterio ships no type stubs (mypy skips it by repository policy).
    """
    from rasterio.transform import Affine

    check_transform_finite(transform)
    return Affine(transform.b, transform.c, transform.a, transform.e, transform.f, transform.d)


def from_affine(affine: Any) -> AffineTransform:
    """Convert a rasterio ``Affine`` to the contract GDAL-order transform.

    Exact inverse of :func:`to_affine` (verified by round-trip test).
    Centralizes the parameter-order mapping so ingestion, mesh and DEM
    code never reimplement it.
    """
    return AffineTransform(
        a=float(affine.c),
        b=float(affine.a),
        c=float(affine.b),
        d=float(affine.f),
        e=float(affine.d),
        f=float(affine.e),
    )


def pixel_to_world(
    transform: AffineTransform,
    col: float,
    row: float,
    anchor: PixelAnchor = PixelAnchor.CENTER,
) -> tuple[float, float]:
    """Map raster coordinates to world (CENTER adds the 0.5 offset)."""
    offset = 0.5 if anchor is PixelAnchor.CENTER else 0.0
    point = to_affine(transform) @ (col + offset, row + offset)
    return (float(point[0]), float(point[1]))


def world_to_pixel(transform: AffineTransform, x: float, y: float) -> tuple[float, float]:
    """Map world coordinates to continuous pixel coordinates (no rounding).

    Returns fractional (col, row); callers choose floor/nearest policy.
    """
    require_invertible(transform)
    point = ~to_affine(transform) @ (x, y)
    return (float(point[0]), float(point[1]))


def raster_bounds(transform: AffineTransform, width: int, height: int) -> Bounds:
    """Derive raster bounds from the four cell corners (no axis assumptions).

    Rasterio's ``array_bounds`` samples two corners assuming north-up
    ordering, which mis-orders south-up rasters and mis-measures
    rotated ones — so all four corners are projected explicitly here
    and normalized with min/max. Same corner math, correct for every
    orientation.
    """
    if width <= 0 or height <= 0:
        raise GeospatialProcessingError(f"raster dimensions must be positive, got {width}x{height}")
    check_transform_finite(transform)
    affine = to_affine(transform)
    corners = [affine @ (c, r) for c, r in ((0, 0), (width, 0), (width, height), (0, height))]
    xs = [float(point[0]) for point in corners]
    ys = [float(point[1]) for point in corners]
    return Bounds(min_x=min(xs), min_y=min(ys), max_x=max(xs), max_y=max(ys))
