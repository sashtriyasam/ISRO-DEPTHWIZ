"""Non-finite values, masks, and sample-contract validation."""

from typing import Any

import pytest
from pydantic import ValidationError

from depthwizard.calibration import CalibrationSamples, ScaleOffsetCalibrator
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.errors import CalibrationError

INF = float("inf")
NAN = float("nan")


def _base(**overrides: Any) -> CalibrationSamples:
    base: dict[str, Any] = {
        "predicted_values": (0.0, 1.0, 2.0, 3.0),
        "reference_values": (10.0, 12.5, 15.0, 17.5),
        "reference_id": "ref-001",
        "reference_units": "meters",
        "target_semantics": ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    }
    base.update(overrides)
    return CalibrationSamples(**base)


def test_nan_predicted_rejected_at_fit() -> None:
    samples = _base(predicted_values=(0.0, NAN, 2.0, 3.0))
    with pytest.raises(CalibrationError, match="non-finite predicted"):
        ScaleOffsetCalibrator().calibrate(samples)


def test_positive_inf_reference_rejected_at_fit() -> None:
    samples = _base(reference_values=(10.0, INF, 15.0, 17.5))
    with pytest.raises(CalibrationError, match="non-finite reference"):
        ScaleOffsetCalibrator().calibrate(samples)


def test_negative_inf_predicted_rejected_at_fit() -> None:
    samples = _base(predicted_values=(0.0, 1.0, -INF, 3.0))
    with pytest.raises(CalibrationError, match="non-finite predicted"):
        ScaleOffsetCalibrator().calibrate(samples)


def test_masked_out_nonfinite_excluded_with_counts() -> None:
    samples = _base(
        predicted_values=(0.0, 1.0, 2.0, NAN),
        valid_mask=(True, True, True, False),
    )
    result = ScaleOffsetCalibrator().calibrate(samples)
    assert result.total_samples == 4
    assert result.valid_samples == 3
    assert result.scale == pytest.approx(2.5, rel=1e-12)


def test_mask_excludes_known_bad_points() -> None:
    samples = _base(
        predicted_values=(0.0, 1.0, 2.0, 100.0),
        reference_values=(10.0, 12.5, 15.0, -999.0),
        valid_mask=(True, True, True, False),
    )
    result = ScaleOffsetCalibrator().calibrate(samples)
    assert result.valid_samples == 3
    assert result.rmse == pytest.approx(0.0, abs=1e-12)


def test_mismatched_lengths_rejected() -> None:
    with pytest.raises(ValidationError, match="counts differ"):
        _base(reference_values=(10.0, 12.5))


def test_bad_mask_length_rejected() -> None:
    with pytest.raises(ValidationError, match="mask length"):
        _base(valid_mask=(True, False))


def test_empty_samples_rejected() -> None:
    with pytest.raises(ValidationError):
        _base(predicted_values=(), reference_values=())


def test_empty_reference_id_rejected() -> None:
    with pytest.raises(ValidationError):
        _base(reference_id="")


def test_non_metric_units_rejected() -> None:
    with pytest.raises(ValidationError, match="metric units"):
        _base(reference_units="feet")


def test_relative_target_semantics_rejected() -> None:
    with pytest.raises(ValidationError, match="metric meaning"):
        _base(target_semantics=ElevationSemantics.RELATIVE_DEPTH)


def test_samples_and_result_immutable() -> None:
    samples = _base()
    result = ScaleOffsetCalibrator().calibrate(samples)
    with pytest.raises(ValidationError):
        samples.reference_id = "mutated"
    with pytest.raises(ValidationError):
        result.scale = 0.0
