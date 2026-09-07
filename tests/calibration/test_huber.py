"""HuberScaleOffsetCalibrator: robust affine with Huber reweighting."""

from __future__ import annotations

import math

import pytest

from depthwizard.calibration import (
    CalibrationSamples,
    HuberScaleOffsetCalibrator,
    ScaleOffsetCalibrator,
)
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.errors import CalibrationError

NOISY_PREDICTED = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0)
NOISE = (0.10, -0.20, 0.15, -0.05, 0.20, -0.10)
NOISY_REFERENCE = tuple(1.5 * p + 5.0 + n for p, n in zip(NOISY_PREDICTED, NOISE, strict=True))


def _samples(**overrides):
    base = {
        "predicted_values": NOISY_PREDICTED,
        "reference_values": NOISY_REFERENCE,
        "reference_id": "ref-huber-001",
        "reference_units": "meters",
        "target_semantics": ElevationSemantics.HEIGHT_AGL_NDSM,
    }
    base.update(overrides)
    return CalibrationSamples(**base)


def test_method_returns_huber():
    assert HuberScaleOffsetCalibrator().method.value == "scale_offset_huber"


def test_huber_close_to_ols_on_clean_noise():
    samples = _samples()
    ols = ScaleOffsetCalibrator().calibrate(samples)
    huber = HuberScaleOffsetCalibrator().calibrate(samples)
    assert huber.scale == pytest.approx(ols.scale, rel=0.05)
    assert huber.offset == pytest.approx(ols.offset, abs=0.2)
    assert huber.valid_samples == 6
    assert huber.rmse > 0.0
    assert huber.mae > 0.0
    assert huber.max_abs_residual > 0.0
    assert huber.r_squared > 0.99


def test_huber_downweights_outlier():
    samples = _samples(
        predicted_values=(0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 10.0),
        reference_values=(5.1, 6.6, 8.1, 9.6, 11.1, 12.6, 18.0),
    )
    huber = HuberScaleOffsetCalibrator().calibrate(samples)
    ScaleOffsetCalibrator().calibrate(samples)
    assert huber.valid_samples == 7
    assert math.isfinite(huber.scale)
    assert math.isfinite(huber.offset)
    assert math.isfinite(huber.rmse)
    assert math.isfinite(huber.mae)
    assert math.isfinite(huber.r_squared)
    assert huber.scale == pytest.approx(1.5, rel=0.2)
    assert huber.offset == pytest.approx(5.0, abs=1.0)


def test_huber_rejects_too_few_samples():
    samples = _samples(
        predicted_values=(0.0, 1.0),
        reference_values=(5.0, 6.5),
    )
    with pytest.raises(CalibrationError, match="at least 3"):
        HuberScaleOffsetCalibrator().calibrate(samples)


def test_huber_rejects_nonfinite_predicted():
    samples = _samples(
        predicted_values=(0.0, 1.0, float("nan"), 3.0),
        reference_values=(5.0, 6.5, 7.0, 8.5),
    )
    with pytest.raises(CalibrationError, match="non-finite predicted"):
        HuberScaleOffsetCalibrator().calibrate(samples)


def test_huber_rejects_nonfinite_reference():
    samples = _samples(
        predicted_values=(0.0, 1.0, 2.0, 3.0),
        reference_values=(5.0, 6.5, float("inf"), 8.5),
    )
    with pytest.raises(CalibrationError, match="non-finite reference"):
        HuberScaleOffsetCalibrator().calibrate(samples)


def test_huber_deterministic():
    samples = _samples()
    first = HuberScaleOffsetCalibrator().calibrate(samples)
    second = HuberScaleOffsetCalibrator().calibrate(samples)
    assert first == second
    assert (first.scale, first.offset) == (second.scale, second.offset)


def test_huber_with_mask():
    samples = _samples(valid_mask=(True, True, True, False, False, False))
    result = HuberScaleOffsetCalibrator().calibrate(samples)
    assert result.valid_samples == 3
    assert result.total_samples == 6
