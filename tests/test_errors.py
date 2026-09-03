"""Deterministic tests for the backend error taxonomy."""

import pytest

from depthwizard import errors


def test_all_expected_errors_exist_and_categorised() -> None:
    expected = {
        errors.InvalidInputError: "invalid_input",
        errors.MissingCRSError: "missing_crs",
        errors.MissingElevationReferenceError: "missing_elevation_reference",
        errors.DemMismatchError: "dem_mismatch",
        errors.InsufficientGCPsError: "insufficient_gcps",
        errors.UnsupportedFormatError: "unsupported_format",
        errors.ModelInferenceError: "model_inference_failure",
        errors.CalibrationError: "calibration_failure",
        errors.MeshGenerationError: "mesh_generation_failure",
        errors.ExportError: "export_failure",
    }
    for cls, code in expected.items():
        assert issubclass(cls, errors.DepthWizardError)
        assert cls.code == code
        err = cls("boom")
        assert isinstance(err, errors.DepthWizardError)
        assert str(err) == "boom"


def test_errors_catchable_as_base() -> None:
    with pytest.raises(errors.DepthWizardError):
        raise errors.CalibrationError("scale solve diverged")


def test_error_codes_are_unique() -> None:
    codes = [
        errors.InvalidInputError.code,
        errors.MissingCRSError.code,
        errors.MissingElevationReferenceError.code,
        errors.DemMismatchError.code,
        errors.InsufficientGCPsError.code,
        errors.UnsupportedFormatError.code,
        errors.ModelInferenceError.code,
        errors.CalibrationError.code,
        errors.MeshGenerationError.code,
        errors.ExportError.code,
    ]
    assert len(set(codes)) == len(codes)
