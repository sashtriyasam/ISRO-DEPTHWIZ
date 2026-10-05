"""Calibration source selection: real references, explicit dev opt-in, refusal."""

from pathlib import Path

import pytest

from depthwizard.backends.synthetic import SyntheticDepthBackend
from depthwizard.calibration import (
    FileBasedCalibrationProvider,
    HuberScaleOffsetCalibrator,
    PiecewiseLinearCalibrator,
    ScaleOffsetCalibrator,
)
from depthwizard.calibration.selection import (
    DEV_CALIBRATION_ENV,
    DEV_REFERENCE_ID,
    DevCalibrationProvider,
    MissingReferenceProvider,
    calibrate_with,
    make_calibrator,
    select_calibration_provider,
)
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.errors import CalibrationError
from depthwizard.ingestion.api import inspect_input
from tests.ingestion.fixtures import make_geotiff, make_png

TARGET = ElevationSemantics.ABSOLUTE_ELEVATION_DSM


def _write_gcps(path: Path) -> Path:
    rows = [(0, 0, 101.0), (4, 0, 104.0), (0, 3, 107.0), (4, 3, 112.0), (2, 1, 105.5)]
    lines = ["pixel_col,pixel_row,elevation"] + [f"{c},{r},{e}" for c, r, e in rows]
    path.write_text("\n".join(lines) + "\n")
    return path


@pytest.mark.parametrize(
    ("method", "expected"),
    [
        ("scale_offset", ScaleOffsetCalibrator),
        ("scale_offset_huber", HuberScaleOffsetCalibrator),
        ("piecewise_linear", PiecewiseLinearCalibrator),
    ],
)
def test_make_calibrator_maps_methods(method: str, expected: type) -> None:
    assert isinstance(make_calibrator(method), expected)


def test_make_calibrator_rejects_unknown_method() -> None:
    with pytest.raises(CalibrationError, match="unsupported calibration method"):
        make_calibrator("magic")


def test_reference_path_selects_file_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(DEV_CALIBRATION_ENV, raising=False)
    provider = select_calibration_provider(str(tmp_path / "gcps.csv"), TARGET)
    assert isinstance(provider, FileBasedCalibrationProvider)


def test_no_reference_refuses_metric_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(DEV_CALIBRATION_ENV, raising=False)
    provider = select_calibration_provider(None, TARGET)
    assert isinstance(provider, MissingReferenceProvider)
    inspection = inspect_input(make_png(tmp_path / "a.png"))
    depth = SyntheticDepthBackend().estimate_depth(inspection)
    with pytest.raises(CalibrationError, match="requires a calibration reference"):
        calibrate_with(provider, inspection, depth)


def test_dev_calibration_requires_explicit_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(DEV_CALIBRATION_ENV, "1")
    provider = select_calibration_provider(None, TARGET, "scale_offset_huber")
    assert isinstance(provider, DevCalibrationProvider)
    inspection = inspect_input(make_png(tmp_path / "a.png"))
    depth = SyntheticDepthBackend().estimate_depth(inspection)
    result = calibrate_with(provider, inspection, depth)
    assert result.reference_id == DEV_REFERENCE_ID
    assert result.method.value == "scale_offset_huber"


def test_file_provider_without_reference_never_fabricates() -> None:
    provider = FileBasedCalibrationProvider(reference_path=None, target=TARGET)
    with pytest.raises(CalibrationError, match="requires a calibration reference"):
        provider.calibrate(None)  # type: ignore[arg-type]


def test_gcp_reference_calibrates_georeferenced_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(DEV_CALIBRATION_ENV, raising=False)
    inspection = inspect_input(make_geotiff(tmp_path / "scene.tif"))
    depth = SyntheticDepthBackend().estimate_depth(inspection)
    gcps = _write_gcps(tmp_path / "gcps.csv")
    provider = select_calibration_provider(str(gcps), TARGET)
    result = calibrate_with(provider, inspection, depth)
    assert result.reference_id == "gcps.csv"
    assert result.reference_units == "meters"
    assert result.valid_samples == 5


def test_gcp_reference_refuses_non_georeferenced_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(DEV_CALIBRATION_ENV, raising=False)
    inspection = inspect_input(make_png(tmp_path / "a.png"))
    depth = SyntheticDepthBackend().estimate_depth(inspection)
    provider = select_calibration_provider(str(_write_gcps(tmp_path / "gcps.csv")), TARGET)
    with pytest.raises(CalibrationError):
        calibrate_with(provider, inspection, depth)
