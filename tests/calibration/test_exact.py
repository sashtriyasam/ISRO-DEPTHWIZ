"""Exact-affine fixture: reference = 2.5 * predicted + 10.

Expected parameters are cross-checked with independent exact rational
arithmetic (Fractions), not re-derived from the implementation.
"""

from fractions import Fraction
from typing import Any

import pytest

from depthwizard.calibration import (
    CalibrationMethod,
    CalibrationResult,
    CalibrationSamples,
    ScaleOffsetCalibrator,
    apply_calibration,
)
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.version import __version__

PREDICTED = (0.0, 1.0, 2.0, 3.0, 4.0)
REFERENCE = tuple(2.5 * p + 10.0 for p in PREDICTED)


def _samples(**overrides: Any) -> CalibrationSamples:
    base: dict[str, Any] = {
        "predicted_values": PREDICTED,
        "reference_values": REFERENCE,
        "reference_id": "ref-exact-001",
        "reference_units": "meters",
        "target_semantics": ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    }
    base.update(overrides)
    return CalibrationSamples(**base)


def _expected_scale_offset() -> tuple[Fraction, Fraction]:
    n = len(PREDICTED)
    xs = [Fraction(str(p)) for p in PREDICTED]
    ys = [Fraction(str(r)) for r in REFERENCE]
    x_bar: Fraction = sum(xs, Fraction(0)) / n
    y_bar: Fraction = sum(ys, Fraction(0)) / n
    s_xx: Fraction = sum(((x - x_bar) ** 2 for x in xs), Fraction(0))
    s_xy: Fraction = sum(
        ((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys, strict=True)), Fraction(0)
    )
    scale: Fraction = s_xy / s_xx
    return scale, y_bar - scale * x_bar


def test_exact_fit_recovers_parameters() -> None:
    result = ScaleOffsetCalibrator().calibrate(_samples())
    exp_scale, exp_offset = _expected_scale_offset()
    assert exp_scale == Fraction(5, 2)
    assert exp_offset == Fraction(10, 1)
    assert result.scale == float(exp_scale) == 2.5
    assert result.offset == float(exp_offset) == 10.0
    assert result.method is CalibrationMethod.SCALE_OFFSET


def test_exact_fit_zero_residuals() -> None:
    result = ScaleOffsetCalibrator().calibrate(_samples())
    assert result.rmse == pytest.approx(0.0, abs=1e-12)
    assert result.mae == pytest.approx(0.0, abs=1e-12)
    assert result.max_abs_residual == pytest.approx(0.0, abs=1e-12)
    assert result.r_squared == 1.0
    assert result.total_samples == 5
    assert result.valid_samples == 5


def test_exact_fit_metadata() -> None:
    result = ScaleOffsetCalibrator().calibrate(
        _samples(reference_checksum="abc123", source_input_id="scene-7")
    )
    assert isinstance(result, CalibrationResult)
    assert result.reference_id == "ref-exact-001"
    assert result.reference_checksum == "abc123"
    assert result.reference_units == "meters"
    assert result.target_semantics is ElevationSemantics.ABSOLUTE_ELEVATION_DSM
    assert result.engine_version == __version__
    assert result.source_input_id == "scene-7"


def test_apply_matches_closed_form() -> None:
    result = ScaleOffsetCalibrator().calibrate(_samples())
    assert apply_calibration(PREDICTED, result) == REFERENCE
    assert apply_calibration((10.0,), result) == (35.0,)
