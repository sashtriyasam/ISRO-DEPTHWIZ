"""PiecewiseLinearCalibrator: local affine per knot interval."""

from __future__ import annotations

import math

import pytest

from depthwizard.calibration import (
    CalibrationSamples,
    PiecewiseLinearCalibrator,
)
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.errors import CalibrationError


def _samples(**overrides):
    base = {
        "predicted_values": (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0),
        "reference_values": (0.0, 2.0, 5.0, 9.0, 14.0, 20.0, 27.0, 35.0),
        "reference_id": "ref-piecewise-001",
        "reference_units": "meters",
        "target_semantics": ElevationSemantics.HEIGHT_AGL_NDSM,
    }
    base.update(overrides)
    return CalibrationSamples(**base)


def test_method_returns_piecewise():
    assert PiecewiseLinearCalibrator().method.value == "piecewise_linear"


def test_default_knots_5():
    cal = PiecewiseLinearCalibrator()
    assert cal._knots == 5


def test_knots_clamped_to_minimum_3():
    cal = PiecewiseLinearCalibrator(knots=1)
    assert cal._knots == 3


def test_piecewise_fits_nonlinear():
    samples = _samples()
    result = PiecewiseLinearCalibrator().calibrate(samples)
    assert result.valid_samples == 8
    assert result.total_samples == 8
    assert result.method.value == "piecewise_linear"
    assert math.isfinite(result.scale)
    assert math.isfinite(result.offset)
    assert math.isfinite(result.rmse)
    assert math.isfinite(result.mae)
    assert math.isfinite(result.max_abs_residual)
    assert math.isfinite(result.r_squared)
    assert result.piecewise_params is not None
    assert len(result.piecewise_params) == 4
    assert result.piecewise_params[0][0] == pytest.approx(0.0)
    assert result.piecewise_params[-1][0] == pytest.approx(5.0)


def test_piecewise_predicts_inside_intervals():
    samples = _samples()
    result = PiecewiseLinearCalibrator().calibrate(samples)
    from depthwizard.calibration import apply_calibration
    preds = apply_calibration(
        (0.0, 3.5, 7.0),
        result,
        piecewise_params=result.piecewise_params,
    )
    assert len(preds) == 3
    assert all(math.isfinite(p) for p in preds)
    assert preds[0] == pytest.approx(0.0, abs=0.5)
    assert preds[1] > 0.0
    assert preds[2] == pytest.approx(35.0, abs=2.0)


def test_piecewise_rejects_too_few_samples():
    samples = _samples(
        predicted_values=(0.0, 1.0),
        reference_values=(0.0, 2.0),
    )
    with pytest.raises(CalibrationError, match="at least 3"):
        PiecewiseLinearCalibrator().calibrate(samples)


def test_piecewise_rejects_nonfinite():
    samples = _samples(
        predicted_values=(0.0, 1.0, float("nan")),
        reference_values=(0.0, 2.0, 5.0),
    )
    with pytest.raises(CalibrationError, match="non-finite predicted"):
        PiecewiseLinearCalibrator().calibrate(samples)


def test_piecewise_deterministic():
    samples = _samples()
    first = PiecewiseLinearCalibrator().calibrate(samples)
    second = PiecewiseLinearCalibrator().calibrate(samples)
    assert first == second
    assert first.piecewise_params == second.piecewise_params


def test_piecewise_with_mask():
    samples = _samples(valid_mask=(True, True, True, False, False, False, False, False))
    result = PiecewiseLinearCalibrator(knots=3).calibrate(samples)
    assert result.valid_samples == 3
    assert result.total_samples == 8
    assert result.piecewise_params is not None
    assert len(result.piecewise_params) == 2
