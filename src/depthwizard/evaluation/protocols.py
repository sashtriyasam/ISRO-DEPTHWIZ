"""Calibration/evaluation split protocols (leakage control).

Calibration pixels must never be counted as held-out evaluation
pixels. The canonical protocol selects deterministic control pixels
(every ``stride``-th valid pixel, plus an offset) for the fit and
scores only the remainder. Controls are never chosen by looking at
test errors.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from depthwizard.calibration import CalibrationResult, CalibrationSamples, ScaleOffsetCalibrator
from depthwizard.contracts.semantics import ElevationSemantics


class CalibrationPlan(BaseModel):
    """How controls were separated from evaluation pixels (JSON-safe)."""

    model_config = ConfigDict(frozen=True)

    protocol: str = Field(
        description="'control-stride' (dense, oracle-like), 'sparse-controls' "
        "(K ground-truth points, GCP-like) or 'sample-split'."
    )
    stride: int | None = Field(default=None, description="Every stride-th pixel calibrates.")
    control_count: int | None = Field(
        default=None, description="Requested control points for 'sparse-controls'."
    )
    offset: int | None = None
    reference_id: str = Field(min_length=1)
    target_semantics: ElevationSemantics
    control_pixels: int = Field(ge=0)
    evaluation_pixels: int = Field(ge=0)


def control_stride_split(
    shape: tuple[int, int],
    valid: np.ndarray,
    stride: int = 8,
    offset: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Split valid pixels into disjoint control/evaluation masks (pure).

    Flat-index pixels with ``(index - offset) % stride == 0`` calibrate;
    all other valid pixels evaluate. The masks are disjoint by
    construction and cover exactly the valid set.
    """
    if stride < 2:
        raise ValueError(f"stride must be >= 2, got {stride}")
    flat_valid = np.asarray(valid, dtype=bool).reshape(-1)
    if flat_valid.size != shape[0] * shape[1]:
        raise ValueError("valid mask does not match the grid shape")
    index = np.arange(flat_valid.size)
    control_flat = flat_valid & ((index - offset) % stride == 0)
    evaluation_flat = flat_valid & ~control_flat
    height, width = shape
    return (
        np.ascontiguousarray(control_flat.reshape(height, width)),
        np.ascontiguousarray(evaluation_flat.reshape(height, width)),
    )


def sparse_control_split(
    shape: tuple[int, int],
    valid: np.ndarray,
    controls: int,
) -> tuple[np.ndarray, np.ndarray]:
    """K evenly spaced valid pixels calibrate; every other valid pixel evaluates.

    Mimics a realistic reference (a handful of GCPs) instead of the dense
    control-stride split, where ~1/stride of the tile's own ground truth
    calibrates and neighbouring, highly correlated pixels are scored —
    close to an in-sample fit. Deterministic; masks are disjoint.
    """
    if controls < 3:
        raise ValueError(f"controls must be >= 3 for an affine fit, got {controls}")
    flat_valid = np.asarray(valid, dtype=bool).reshape(-1)
    if flat_valid.size != shape[0] * shape[1]:
        raise ValueError("valid mask does not match the grid shape")
    valid_index = np.flatnonzero(flat_valid)
    if valid_index.size <= controls:
        raise ValueError(
            f"only {valid_index.size} valid pixels; need more than {controls} controls"
        )
    picks = np.unique(np.linspace(0, valid_index.size - 1, controls).round().astype(np.int64))
    control_flat = np.zeros(flat_valid.size, dtype=bool)
    control_flat[valid_index[picks]] = True
    evaluation_flat = flat_valid & ~control_flat
    height, width = shape
    return (
        np.ascontiguousarray(control_flat.reshape(height, width)),
        np.ascontiguousarray(evaluation_flat.reshape(height, width)),
    )


def fit_controls(
    predicted: np.ndarray,
    reference: np.ndarray,
    control_mask: np.ndarray,
    reference_id: str,
    target: ElevationSemantics,
    source_checksum: str | None,
) -> CalibrationResult:
    """Fit the affine map on control pixels only (real OLS calibrator)."""
    predicted = np.asarray(predicted, dtype=np.float64)
    reference = np.asarray(reference, dtype=np.float64)
    mask = np.asarray(control_mask, dtype=bool)
    if not mask.any():
        raise ValueError("CALIBRATION_INVALID: no control pixels in split")
    samples = CalibrationSamples(
        predicted_values=tuple(float(value) for value in predicted[mask]),
        reference_values=tuple(float(value) for value in reference[mask]),
        reference_id=reference_id,
        reference_units="meters",
        target_semantics=target,
        source_checksum=source_checksum,
    )
    return ScaleOffsetCalibrator().calibrate(samples)
