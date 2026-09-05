"""Grid compatibility gate: refuse silent misalignment.

Pixel-native rasters (no CRS, e.g. GAMUS tiles) must match dimensions
exactly (method ``native-pixel``). CRS-backed rasters reuse the
canonical ``geospatial`` machinery: ``COMPATIBLE`` passes through,
anything else requires an explicitly declared alignment step and is
otherwise refused. Interpolated values are never called ground truth.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AlignmentReport(BaseModel):
    """How prediction and reference grids were related (JSON-safe)."""

    model_config = ConfigDict(frozen=True)

    method: str = Field(
        description="'native-pixel', 'compatible', or an explicit reproject record."
    )
    resampled: bool = Field(description="True only when interpolation was applied.")
    resampling: str | None = None
    source_shape: tuple[int, int] = Field(description="(height, width) of the prediction grid.")
    target_shape: tuple[int, int] = Field(description="(height, width) of the reference grid.")
    source_crs: str | None = None
    target_crs: str | None = None


def check_pixel_compatibility(
    pred_shape: tuple[int, int],
    ref_shape: tuple[int, int],
    pred_crs: str | None = None,
    ref_crs: str | None = None,
) -> AlignmentReport:
    """Gate comparison grids (pure; raises on any silent mismatch)."""
    if (pred_crs is None) != (ref_crs is None):
        raise ValueError(
            "GRID_MISMATCH: one grid carries a CRS and the other does not; "
            "refusing to compare without an explicit alignment step"
        )
    if pred_crs is not None and ref_crs is not None:
        if pred_crs != ref_crs:
            raise ValueError(
                f"GRID_MISMATCH: CRS differs ({pred_crs!r} vs {ref_crs!r}); "
                "declare an explicit reprojection step"
            )
        if pred_shape != ref_shape:
            raise ValueError(
                f"GRID_MISMATCH: shared-CRS grids differ in shape {pred_shape} vs {ref_shape}"
            )
        return AlignmentReport(
            method="compatible",
            resampled=False,
            resampling=None,
            source_shape=pred_shape,
            target_shape=ref_shape,
            source_crs=pred_crs,
            target_crs=ref_crs,
        )
    if pred_shape != ref_shape:
        raise ValueError(
            f"GRID_MISMATCH: pixel-native grids differ in shape {pred_shape} vs {ref_shape}"
        )
    return AlignmentReport(
        method="native-pixel",
        resampled=False,
        resampling=None,
        source_shape=pred_shape,
        target_shape=ref_shape,
        source_crs=None,
        target_crs=None,
    )
