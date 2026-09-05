"""Deterministic error metrics over explicit valid-pixel masks.

Valid pixel = predicted finite AND reference finite AND reference
valid. NaN/nodata/inf never become zero; they are excluded and
counted. Coverage describes coverage — not accuracy, not confidence.

R² follows the ``CalibrationResult`` convention: 1.0 when a constant
reference is matched perfectly, else 0.0; ``None`` is never returned —
an empty valid set is an error (``NO_VALID_PIXELS``), not a score.
"""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class MetricSummary(BaseModel):
    """Metric values with the counts that produced them (JSON-safe)."""

    model_config = ConfigDict(frozen=True)

    units: str = Field(description="Metric units ('meters').")
    total_pixels: int = Field(ge=0)
    valid_pixels: int = Field(ge=0)
    invalid_pixels: int = Field(ge=0)
    coverage_fraction: float = Field(ge=0.0, le=1.0)
    mae: float = Field(ge=0.0)
    rmse: float = Field(ge=0.0)
    r_squared: float = Field(description="Pooled 1 - SSres/SStot; constant-ref convention.")
    median_abs_error: float = Field(ge=0.0)
    max_abs_error: float = Field(ge=0.0)


def valid_evaluation_mask(
    predicted: np.ndarray,
    reference: np.ndarray,
    reference_valid: np.ndarray | None = None,
) -> np.ndarray:
    """Build the deterministic valid-pixel mask (pure)."""
    predicted = np.asarray(predicted, dtype=np.float64)
    reference = np.asarray(reference, dtype=np.float64)
    if predicted.shape != reference.shape:
        raise ValueError(f"shape mismatch: {predicted.shape} vs {reference.shape}")
    mask = np.isfinite(predicted) & np.isfinite(reference)
    if reference_valid is not None:
        valid = np.asarray(reference_valid, dtype=bool)
        if valid.shape != mask.shape:
            raise ValueError(f"mask shape mismatch: {valid.shape} vs {mask.shape}")
        mask = mask & valid
    return np.ascontiguousarray(mask)


def _r_squared(errors: np.ndarray, reference: np.ndarray) -> float:
    """Pooled R² with the constant-reference convention."""
    ss_res = float(np.sum(errors * errors))
    mean = float(np.mean(reference))
    ss_tot = float(np.sum((reference - mean) ** 2))
    if ss_tot == 0.0:
        return 1.0 if ss_res == 0.0 else 0.0
    return 1.0 - ss_res / ss_tot


def compute_metrics(
    predicted: np.ndarray,
    reference: np.ndarray,
    reference_valid: np.ndarray | None = None,
    units: str = "meters",
) -> MetricSummary:
    """Score calibrated metric predictions against a metric reference."""
    if units != "meters":
        raise ValueError(f"metric evaluation requires units='meters', got {units!r}")
    mask = valid_evaluation_mask(predicted, reference, reference_valid)
    total = int(mask.size)
    valid = int(mask.sum())
    if valid == 0:
        raise ValueError("NO_VALID_PIXELS: no pixels available for scoring")
    pred = np.asarray(predicted, dtype=np.float64)[mask]
    ref = np.asarray(reference, dtype=np.float64)[mask]
    errors = pred - ref
    abs_errors = np.abs(errors)
    return MetricSummary(
        units=units,
        total_pixels=total,
        valid_pixels=valid,
        invalid_pixels=total - valid,
        coverage_fraction=valid / total,
        mae=float(np.mean(abs_errors)),
        rmse=float(math.sqrt(float(np.mean(errors * errors)))),
        r_squared=_r_squared(errors, ref),
        median_abs_error=float(np.median(abs_errors)),
        max_abs_error=float(np.max(abs_errors)),
    )


def pool_metric_summaries(summaries: list[MetricSummary]) -> dict[str, float]:
    """Macro-average per-sample summaries (pooled scoring lives in the runner).

    Macro averages describe the typical sample; pooled pixelwise scoring
    (concatenated valid pixels) is the primary run metric and is computed
    separately by the runner from raw error accumulators.
    """
    if not summaries:
        raise ValueError("no summaries to aggregate")
    keys = ("mae", "rmse", "r_squared", "median_abs_error", "max_abs_error", "coverage_fraction")
    return {
        key: float(sum(getattr(summary, key) for summary in summaries) / len(summaries))
        for key in keys
    }


class PooledAccumulator:
    """Exact pooled MAE/RMSE/R² from scalar accumulators (no pixel retention).

    Maintains count, Σ|e|, Σe², Σy, Σy², max|e| over concatenated held-out
    errors ``e`` and references ``y``. Pooled R² = 1 − Σe²/(Σy² − (Σy)²/n)
    with the constant-reference convention (1.0 if exact else 0.0).
    Memory is O(1) in pixel count.
    """

    def __init__(self) -> None:
        """Start empty."""
        self.count = 0
        self.sum_abs = 0.0
        self.sum_sq_err = 0.0
        self.sum_y = 0.0
        self.sum_y2 = 0.0
        self.max_abs = 0.0

    def add(self, errors: np.ndarray, references: np.ndarray) -> None:
        """Fold one sample's held-out errors/references (finite only)."""
        errors = np.asarray(errors, dtype=np.float64).ravel()
        references = np.asarray(references, dtype=np.float64).ravel()
        if errors.shape != references.shape:
            raise ValueError("accumulator error/reference shape mismatch")
        finite = np.isfinite(errors) & np.isfinite(references)
        errors = errors[finite]
        references = references[finite]
        absolute = np.abs(errors)
        self.count += int(errors.size)
        self.sum_abs += float(np.sum(absolute))
        self.sum_sq_err += float(np.sum(errors * errors))
        self.sum_y += float(np.sum(references))
        self.sum_y2 += float(np.sum(references * references))
        if absolute.size:
            self.max_abs = max(self.max_abs, float(np.max(absolute)))

    def summary(self) -> dict[str, float]:
        """Emit pooled MAE/RMSE/R²/max from accumulated scalars."""
        if self.count == 0:
            raise ValueError("NO_VALID_PIXELS: accumulator is empty")
        ss_tot = self.sum_y2 - (self.sum_y * self.sum_y) / self.count
        if ss_tot == 0.0:
            r_squared = 1.0 if self.sum_sq_err == 0.0 else 0.0
        else:
            r_squared = 1.0 - self.sum_sq_err / ss_tot
        return {
            "mae": self.sum_abs / self.count,
            "rmse": math.sqrt(self.sum_sq_err / self.count),
            "r_squared": r_squared,
            "max_abs_error": self.max_abs,
            "count": float(self.count),
        }
