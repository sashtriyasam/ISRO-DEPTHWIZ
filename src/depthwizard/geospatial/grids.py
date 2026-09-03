"""Generic spatial target grids, compatibility and alignment status.

``TargetGrid`` is the typed contract for reprojection/alignment
targets (and, symmetrically, for describing any raster's spatial
footprint): CRS, affine, dimensions, dtype, nodata and optional
resolution. It is intentionally not another DSMGrid — future DEM,
imagery and predicted-surface alignment all need a meaning-free
spatial grid description.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.contracts.spatial import AffineTransform
from depthwizard.errors import GeospatialProcessingError
from depthwizard.geospatial.crs import crs_equal
from depthwizard.geospatial.transforms import check_transform_finite

#: Per-parameter absolute tolerance base for affine comparison. Affine
#: origins near 1e6 with rel_tol=1e-9 resolve millimetre-level
#: agreement; anything coarser would silently accept shifted grids.
_COMPARE_REL_TOL = 1e-9


class AlignmentStatus(str, Enum):
    """Spatial relationship between two rasters.

    COMPATIBLE: cell-for-cell use without reprojection/resampling.
    REPROJECTABLE: transformation is possible (valid CRS/grids both sides).
    INCOMPATIBLE: required metadata absent/invalid or no safe relation.
    """

    COMPATIBLE = "compatible"
    REPROJECTABLE = "reprojectable"
    INCOMPATIBLE = "incompatible"


class TargetGrid(BaseModel):
    """Explicit reprojection/alignment grid (CRS mandatory)."""

    model_config = ConfigDict(frozen=True)

    crs: str = Field(min_length=1)
    transform: AffineTransform
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    dtype: str = Field(description="Storage dtype name, e.g. 'float32'.")
    nodata: float
    resolution: float | None = Field(
        default=None, gt=0, description="Ground sampling distance, when known."
    )

    @model_validator(mode="after")
    def _check_grid(self) -> TargetGrid:
        check_transform_finite(self.transform)
        return self


class CompatibilityResult(BaseModel):
    """Detailed compatibility verdict (reasons, never a bare boolean)."""

    model_config = ConfigDict(frozen=True)

    compatible: bool
    reasons: tuple[str, ...] = Field(
        default=(), description="Empty when compatible; mismatch notes otherwise."
    )


def _close(first: float, second: float) -> bool:
    """Deterministic float comparison for affine parameters."""
    import math

    return math.isclose(first, second, rel_tol=_COMPARE_REL_TOL, abs_tol=0.0)


def check_grid_compatibility(first: TargetGrid, second: TargetGrid) -> CompatibilityResult:
    """Check cell-for-cell usability (dims, CRS, transform, resolution)."""
    reasons: list[str] = []
    if first.width != second.width or first.height != second.height:
        reasons.append(
            f"dimensions {(first.width, first.height)} != {(second.width, second.height)}"
        )
    try:
        same_crs = crs_equal(first.crs, second.crs)
    except GeospatialProcessingError as exc:
        return CompatibilityResult(compatible=False, reasons=(f"invalid CRS: {exc}",))
    if not same_crs:
        reasons.append(f"CRS {first.crs!r} != {second.crs!r}")
    params = (
        ("a", first.transform.a, second.transform.a),
        ("b", first.transform.b, second.transform.b),
        ("c", first.transform.c, second.transform.c),
        ("d", first.transform.d, second.transform.d),
        ("e", first.transform.e, second.transform.e),
        ("f", first.transform.f, second.transform.f),
    )
    differing = [name for name, left, right in params if not _close(left, right)]
    if differing:
        reasons.append(f"affine parameters differ: {', '.join(differing)}")
    if first.resolution is not None and second.resolution is not None:
        if not _close(first.resolution, second.resolution):
            reasons.append(f"resolution {first.resolution} != {second.resolution}")
    return CompatibilityResult(compatible=not reasons, reasons=tuple(reasons))


def classify_alignment(first: TargetGrid, second: TargetGrid) -> AlignmentStatus:
    """Decide the spatial relationship (detail via check_grid_compatibility)."""
    if check_grid_compatibility(first, second).compatible:
        return AlignmentStatus.COMPATIBLE
    try:
        crs_equal(first.crs, second.crs)
    except GeospatialProcessingError:
        return AlignmentStatus.INCOMPATIBLE
    return AlignmentStatus.REPROJECTABLE
