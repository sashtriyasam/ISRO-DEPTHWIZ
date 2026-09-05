"""Sample-level bootstrap uncertainty (descriptive first, inference honestly).

Resampling unit is the tile/sample — never the pixel. Millions of
spatially correlated pixels are not independent observations, so
pixel-level resampling is refused by design. Each group comparison
reports the observed delta, a percentile interval, exact sample
counts, the seed, and an adequacy flag; groups below
``MIN_SAMPLES_FOR_INFERENCE`` are labelled descriptive-only. No
p-values are produced.
"""

from __future__ import annotations

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

#: Minimum per-group samples before an interval is called inferential.
MIN_SAMPLES_FOR_INFERENCE = 10

#: Default resamples and confidence level.
DEFAULT_RESAMPLES = 2000
DEFAULT_CONFIDENCE = 0.95
DEFAULT_SEED = 26175


class GroupComparison(BaseModel):
    """One two-group comparison with full resampling provenance."""

    model_config = ConfigDict(frozen=True)

    metric: str = Field(min_length=1, description="Compared per-sample metric (e.g. 'mae').")
    group_a: str = Field(min_length=1)
    group_b: str = Field(min_length=1)
    n_a: int = Field(ge=0)
    n_b: int = Field(ge=0)
    observed_a: float
    observed_b: float
    observed_delta: float = Field(description="mean(a) - mean(b).")
    ci_low: float
    ci_high: float
    confidence: float = Field(gt=0.0, lt=1.0)
    resamples: int = Field(gt=0)
    seed: int
    method: str = Field(description="'two-sample-bootstrap' (unpaired groups).")
    adequately_powered: bool = Field(description="False unless both groups meet the minimum.")
    note: str = Field(description="descriptive-only caveat when underpowered.")


class GroupInterval(BaseModel):
    """Single-group mean with a sample-level bootstrap interval."""

    model_config = ConfigDict(frozen=True)

    metric: str = Field(min_length=1)
    group: str = Field(min_length=1)
    n: int = Field(ge=0)
    observed_mean: float
    ci_low: float
    ci_high: float
    confidence: float = Field(gt=0.0, lt=1.0)
    resamples: int = Field(gt=0)
    seed: int
    method: str = Field(description="'sample-bootstrap'.")
    adequately_powered: bool
    note: str


def _percentile_interval(draws: np.ndarray, confidence: float) -> tuple[float, float]:
    """Two-sided percentile interval (pure)."""
    alpha = (1.0 - confidence) / 2.0
    return float(np.quantile(draws, alpha)), float(np.quantile(draws, 1.0 - alpha))


def _check_values(values: np.ndarray, label: str) -> np.ndarray:
    """Finite 1-D sample vector or a structured refusal."""
    array = np.asarray(values, dtype=np.float64).ravel()
    if array.size == 0:
        raise ValueError(f"EVALUATION_FAILED: no {label} samples for comparison")
    if not np.isfinite(array).all():
        raise ValueError(f"EVALUATION_FAILED: non-finite {label} metric values")
    return array


def bootstrap_mean_interval(
    values: np.ndarray,
    group: str,
    metric: str,
    seed: int = DEFAULT_SEED,
    resamples: int = DEFAULT_RESAMPLES,
    confidence: float = DEFAULT_CONFIDENCE,
) -> GroupInterval:
    """Bootstrap CI for a group mean over tiles (deterministic seed)."""
    array = _check_values(values, "group")
    generator = np.random.default_rng(seed)
    draws = np.empty(resamples)
    for index in range(resamples):
        draws[index] = float(np.mean(generator.choice(array, size=array.size, replace=True)))
    low, high = _percentile_interval(draws, confidence)
    powered = array.size >= MIN_SAMPLES_FOR_INFERENCE
    return GroupInterval(
        metric=metric,
        group=group,
        n=int(array.size),
        observed_mean=float(np.mean(array)),
        ci_low=low,
        ci_high=high,
        confidence=confidence,
        resamples=resamples,
        seed=seed,
        method="sample-bootstrap",
        adequately_powered=powered,
        note=(
            "inferential interval"
            if powered
            else f"descriptive only: n={array.size} < {MIN_SAMPLES_FOR_INFERENCE} "
            "(underpowered for robust inference)"
        ),
    )


def compare_groups(
    values_a: np.ndarray,
    values_b: np.ndarray,
    group_a: str,
    group_b: str,
    metric: str,
    seed: int = DEFAULT_SEED,
    resamples: int = DEFAULT_RESAMPLES,
    confidence: float = DEFAULT_CONFIDENCE,
) -> GroupComparison:
    """Two-sample bootstrap CI for mean(a) - mean(b), unpaired groups."""
    array_a = _check_values(values_a, group_a)
    array_b = _check_values(values_b, group_b)
    generator = np.random.default_rng(seed)
    draws = np.empty(resamples)
    for index in range(resamples):
        mean_a = float(np.mean(generator.choice(array_a, size=array_a.size, replace=True)))
        mean_b = float(np.mean(generator.choice(array_b, size=array_b.size, replace=True)))
        draws[index] = mean_a - mean_b
    low, high = _percentile_interval(draws, confidence)
    powered = (
        array_a.size >= MIN_SAMPLES_FOR_INFERENCE and array_b.size >= MIN_SAMPLES_FOR_INFERENCE
    )
    observed_delta = float(np.mean(array_a) - np.mean(array_b))
    return GroupComparison(
        metric=metric,
        group_a=group_a,
        group_b=group_b,
        n_a=int(array_a.size),
        n_b=int(array_b.size),
        observed_a=float(np.mean(array_a)),
        observed_b=float(np.mean(array_b)),
        observed_delta=observed_delta,
        ci_low=low,
        ci_high=high,
        confidence=confidence,
        resamples=resamples,
        seed=seed,
        method="two-sample-bootstrap",
        adequately_powered=powered,
        note=(
            "inferential interval"
            if powered
            else f"descriptive only: n_a={array_a.size}, n_b={array_b.size} "
            f"(minimum {MIN_SAMPLES_FOR_INFERENCE} per group for robust inference)"
        ),
    )
