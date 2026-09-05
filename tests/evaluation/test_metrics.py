"""Metric correctness, nodata policy, coverage, aggregation."""

from __future__ import annotations

import math

import numpy as np
import pytest

from depthwizard.evaluation.metrics import (
    compute_metrics,
    pool_metric_summaries,
    valid_evaluation_mask,
)


def test_exact_known_values() -> None:
    """Hand-computed MAE/RMSE/R2 on a tiny grid."""
    predicted = np.array([[1.0, 2.0], [3.0, 4.0]])
    reference = np.array([[1.0, 2.0], [3.0, 5.0]])
    summary = compute_metrics(predicted, reference)
    assert summary.mae == pytest.approx(0.25)
    assert summary.rmse == pytest.approx(0.5)
    # errors^2 = 1, mean(ref) = 2.75, SStot = 8.75 -> R2 = 1 - 1/8.75
    assert summary.r_squared == pytest.approx(1.0 - 1.0 / 8.75)
    assert summary.median_abs_error == pytest.approx(0.0)
    assert summary.max_abs_error == pytest.approx(1.0)
    assert summary.valid_pixels == 4
    assert summary.coverage_fraction == pytest.approx(1.0)


def test_nodata_excluded_not_zeroed() -> None:
    """NaN reference pixels are excluded and counted, never zero-filled."""
    predicted = np.array([[1.0, 2.0], [3.0, 4.0]])
    reference = np.array([[1.0, float("nan")], [3.0, 4.0]])
    summary = compute_metrics(predicted, reference)
    assert summary.valid_pixels == 3
    assert summary.invalid_pixels == 1
    assert summary.coverage_fraction == pytest.approx(0.75)
    assert summary.mae == pytest.approx(0.0)


def test_nonfinite_prediction_excluded() -> None:
    """inf predictions are excluded, not clamped."""
    predicted = np.array([[1.0, float("inf")], [3.0, 4.0]])
    reference = np.array([[1.0, 2.0], [3.0, 4.0]])
    summary = compute_metrics(predicted, reference)
    assert summary.valid_pixels == 3
    assert summary.mae == pytest.approx(0.0)


def test_reference_mask_respected() -> None:
    """An explicit reference valid mask further restricts scoring."""
    predicted = np.ones((2, 2))
    reference = np.ones((2, 2))
    mask = np.array([[True, False], [True, True]])
    summary = compute_metrics(predicted, reference, mask)
    assert summary.valid_pixels == 3
    assert summary.invalid_pixels == 1


def test_valid_zero_stays_valid() -> None:
    """Zero is a legitimate elevation, not a missing-value sentinel."""
    predicted = np.zeros((2, 2))
    reference = np.zeros((2, 2))
    summary = compute_metrics(predicted, reference)
    assert summary.valid_pixels == 4
    assert summary.mae == pytest.approx(0.0)
    assert summary.r_squared == pytest.approx(1.0)


def test_no_valid_pixels_is_error() -> None:
    """Empty scoring sets raise instead of returning vacuous zeros."""
    with pytest.raises(ValueError, match="NO_VALID_PIXELS"):
        compute_metrics(
            np.array([[1.0]]),
            np.array([[float("nan")]]),
        )


def test_units_must_be_meters() -> None:
    """Relative/unitless comparisons are refused at the metric gate."""
    with pytest.raises(ValueError, match="meters"):
        compute_metrics(np.ones((2, 2)), np.ones((2, 2)), units="relative")


def test_shape_mismatch_rejected() -> None:
    """Comparisons require identical grids."""
    with pytest.raises(ValueError, match="shape mismatch"):
        valid_evaluation_mask(np.ones((2, 2)), np.ones((3, 3)))


def test_constant_reference_convention() -> None:
    """Constant references use the 1.0/0.0 convention, never NaN R2."""
    perfect = compute_metrics(np.full((2, 2), 5.0), np.full((2, 2), 5.0))
    assert perfect.r_squared == pytest.approx(1.0)
    imperfect = compute_metrics(np.full((2, 2), 6.0), np.full((2, 2), 5.0))
    assert imperfect.r_squared == pytest.approx(0.0)
    assert imperfect.mae == pytest.approx(1.0)


def test_macro_average_is_distinct_from_pooled() -> None:
    """Macro means describe typical samples; pooled scoring is separate."""
    first = compute_metrics(np.array([[0.0, 0.0]]), np.array([[0.0, 0.0]]))
    second = compute_metrics(np.array([[0.0, 10.0]]), np.array([[0.0, 0.0]]))
    macro = pool_metric_summaries([first, second])
    assert macro["mae"] == pytest.approx((0.0 + 5.0) / 2)
    assert macro["coverage_fraction"] == pytest.approx(1.0)
    with pytest.raises(ValueError, match="no summaries"):
        pool_metric_summaries([])


def test_reproducibility_same_fixture_same_result() -> None:
    """Identical inputs produce identical summaries."""
    predicted = np.array([[1.5, 2.5], [3.5, 4.5]])
    reference = np.array([[1.0, 2.0], [4.0, 4.0]])
    first = compute_metrics(predicted, reference)
    second = compute_metrics(predicted.copy(), reference.copy())
    assert first == second
    assert math.isfinite(first.rmse)
