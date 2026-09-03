"""Noisy data, degenerate predictors and minimum-sample enforcement."""

from typing import Any

import pytest

from depthwizard.calibration import (
    MIN_VALID_SAMPLES,
    CalibrationSamples,
    ScaleOffsetCalibrator,
)
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.errors import CalibrationError

NOISY_PREDICTED = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)
NOISE = (0.10, -0.20, 0.15, -0.05, 0.20, -0.10)
NOISY_REFERENCE = tuple(1.5 * p + 5.0 + n for p, n in zip(NOISY_PREDICTED, NOISE, strict=True))


def _noisy(**overrides: Any) -> CalibrationSamples:
    base: dict[str, Any] = {
        "predicted_values": NOISY_PREDICTED,
        "reference_values": NOISY_REFERENCE,
        "reference_id": "ref-noisy-001",
        "reference_units": "meters",
        "target_semantics": ElevationSemantics.HEIGHT_AGL_NDSM,
    }
    base.update(overrides)
    return CalibrationSamples(**base)


def test_noisy_fit_finite_and_directional() -> None:
    calibrator = ScaleOffsetCalibrator()
    result = calibrator.calibrate(_noisy())
    assert result.scale == pytest.approx(1.5, rel=0.05)
    assert result.offset == pytest.approx(5.0, abs=0.2)
    assert result.rmse > 0.0
    assert result.rmse < 0.3
    assert result.mae > 0.0
    assert result.max_abs_residual > 0.0
    assert result.r_squared > 0.99
    assert result.valid_samples == 6


def test_noisy_fit_deterministic() -> None:
    calibrator = ScaleOffsetCalibrator()
    first = calibrator.calibrate(_noisy())
    second = calibrator.calibrate(_noisy())
    assert first == second
    assert (first.scale, first.offset) == (second.scale, second.offset)


def test_degenerate_constant_predictor() -> None:
    samples = _noisy(
        predicted_values=(3.0, 3.0, 3.0, 3.0, 3.0),
        reference_values=(1.0, 2.0, 3.0, 4.0, 5.0),
    )
    with pytest.raises(CalibrationError, match="zero variance"):
        ScaleOffsetCalibrator().calibrate(samples)


def test_degenerate_constant_predictor_and_reference() -> None:
    samples = _noisy(
        predicted_values=(3.0, 3.0, 3.0),
        reference_values=(7.0, 7.0, 7.0),
    )
    with pytest.raises(CalibrationError, match="zero variance"):
        ScaleOffsetCalibrator().calibrate(samples)


def test_minimum_samples_enforced() -> None:
    assert MIN_VALID_SAMPLES == 3
    two = _noisy(
        predicted_values=(0.0, 1.0),
        reference_values=(10.0, 12.5),
    )
    with pytest.raises(CalibrationError, match="at least 3"):
        ScaleOffsetCalibrator().calibrate(two)


def test_mask_reducing_below_minimum() -> None:
    samples = _noisy(
        valid_mask=(True, True, False, False, False, False),
    )
    with pytest.raises(CalibrationError, match="at least 3"):
        ScaleOffsetCalibrator().calibrate(samples)


def test_exactly_three_samples_fit() -> None:
    samples = _noisy(
        predicted_values=(0.0, 1.0, 2.0),
        reference_values=(10.0, 12.5, 15.0),
    )
    result = ScaleOffsetCalibrator().calibrate(samples)
    assert result.valid_samples == 3
    assert result.scale == pytest.approx(2.5, rel=1e-12)
    assert result.offset == pytest.approx(10.0, rel=1e-12)
