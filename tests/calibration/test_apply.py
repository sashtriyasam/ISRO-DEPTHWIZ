"""apply_calibration: purity, cardinality, precision, failure modes."""

import pytest

from depthwizard.calibration import (
    CalibrationResult,
    CalibrationSamples,
    ScaleOffsetCalibrator,
    apply_calibration,
)
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.errors import CalibrationError


def _result() -> CalibrationResult:
    samples = CalibrationSamples(
        predicted_values=(0.0, 1.0, 2.0, 3.0, 4.0),
        reference_values=(10.0, 12.5, 15.0, 17.5, 20.0),
        reference_id="ref-apply-001",
        reference_units="meters",
        target_semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
    )
    return ScaleOffsetCalibrator().calibrate(samples)


def test_apply_matches_scale_offset() -> None:
    result = _result()
    assert result.scale == 2.5
    assert result.offset == 10.0
    assert apply_calibration((0.0, 1.0, 2.0), result) == (10.0, 12.5, 15.0)


def test_apply_preserves_cardinality_and_empty() -> None:
    result = _result()
    assert apply_calibration((), result) == ()
    assert len(apply_calibration(range(7), result)) == 7


def test_apply_does_not_mutate_input() -> None:
    result = _result()
    source = [1.0, 2.0, 3.0]
    snapshot = list(source)
    assert apply_calibration(source, result) == (12.5, 15.0, 17.5)
    assert source == snapshot


def test_apply_deterministic() -> None:
    result = _result()
    assert apply_calibration((4.0, 5.0), result) == apply_calibration((4.0, 5.0), result)


def test_apply_rejects_nonfinite_input() -> None:
    result = _result()
    with pytest.raises(CalibrationError, match="non-finite input"):
        apply_calibration((1.0, float("nan")), result)
    with pytest.raises(CalibrationError, match="non-finite input"):
        apply_calibration((float("inf"),), result)


def test_apply_rejects_overflow_output() -> None:
    result = _result().model_copy(update={"scale": 1e308, "offset": 0.0})
    with pytest.raises(CalibrationError, match="non-finite calibrated"):
        apply_calibration((1e308,), result)


def test_apply_rejects_non_result_calibration() -> None:
    with pytest.raises(TypeError, match="CalibrationResult"):
        apply_calibration((1.0,), "not-a-result")  # type: ignore[arg-type]


def test_result_source_values_untouched_by_apply() -> None:
    samples = CalibrationSamples(
        predicted_values=(0.0, 1.0, 2.0, 3.0, 4.0),
        reference_values=(10.0, 12.5, 15.0, 17.5, 20.0),
        reference_id="ref-apply-002",
        reference_units="meters",
        target_semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
    )
    before = (samples.predicted_values, samples.reference_values)
    result = ScaleOffsetCalibrator().calibrate(samples)
    apply_calibration(samples.predicted_values, result)
    assert (samples.predicted_values, samples.reference_values) == before
