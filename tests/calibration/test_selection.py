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


def _depth_on_geotiff(tmp_path: Path):  # type: ignore[no-untyped-def]
    inspection = inspect_input(make_geotiff(tmp_path / "scene.tif"))
    return inspection, SyntheticDepthBackend().estimate_depth(inspection)


def test_dem_reference_cannot_back_agl_target(tmp_path: Path) -> None:
    inspection, depth = _depth_on_geotiff(tmp_path)
    provider = FileBasedCalibrationProvider(
        reference_path=str(tmp_path / "dem.tif"), target=ElevationSemantics.HEIGHT_AGL_NDSM
    )
    with pytest.raises(CalibrationError, match="absolute terrain elevations"):
        calibrate_with(provider, inspection, depth)


def test_gcp_column_must_match_target(tmp_path: Path) -> None:
    inspection, depth = _depth_on_geotiff(tmp_path)
    gcps = _write_gcps(tmp_path / "gcps.csv")  # 'elevation' column
    provider = FileBasedCalibrationProvider(
        reference_path=str(gcps), target=ElevationSemantics.HEIGHT_AGL_NDSM
    )
    with pytest.raises(CalibrationError, match="needs a 'height_agl' column"):
        calibrate_with(provider, inspection, depth)


def test_gcp_height_agl_column_backs_agl_target(tmp_path: Path) -> None:
    inspection, depth = _depth_on_geotiff(tmp_path)
    path = tmp_path / "agl.csv"
    path.write_text("pixel_col,pixel_row,height_agl\n0,0,1\n4,0,4\n0,3,7\n4,3,12\n2,1,5.5\n")
    provider = FileBasedCalibrationProvider(
        reference_path=str(path), target=ElevationSemantics.HEIGHT_AGL_NDSM
    )
    result = calibrate_with(provider, inspection, depth)
    assert result.target_semantics is ElevationSemantics.HEIGHT_AGL_NDSM
    assert result.valid_samples == 5


def test_gcp_csv_with_excel_bom_is_read(tmp_path: Path) -> None:
    inspection, depth = _depth_on_geotiff(tmp_path)
    path = tmp_path / "bom.csv"
    path.write_bytes("﻿pixel_col,pixel_row,elevation\n0,0,1\n4,0,4\n0,3,7\n".encode())
    provider = select_calibration_provider(str(path), TARGET)
    assert calibrate_with(provider, inspection, depth).valid_samples == 3


def test_malformed_gcp_csv_is_a_calibration_error(tmp_path: Path) -> None:
    inspection, depth = _depth_on_geotiff(tmp_path)
    path = tmp_path / "bad.csv"
    path.write_text("pixel_col,pixel_row,elevation\n0,0,abc\n")
    with pytest.raises(CalibrationError, match="row 2 is not numeric"):
        calibrate_with(select_calibration_provider(str(path), TARGET), inspection, depth)
    path.write_text("x,y,z\n0,0,1\n")
    with pytest.raises(CalibrationError, match="GCP CSV needs columns"):
        calibrate_with(select_calibration_provider(str(path), TARGET), inspection, depth)


def test_weak_fit_is_flagged_and_good_fit_is_not() -> None:
    from depthwizard.calibration import CalibrationSamples, ScaleOffsetCalibrator
    from depthwizard.calibration.selection import fit_quality_warnings

    def fit(reference: tuple[float, ...]):  # type: ignore[no-untyped-def]
        return ScaleOffsetCalibrator().calibrate(
            CalibrationSamples(
                predicted_values=(0.0, 1.0, 2.0, 3.0, 4.0, 5.0),
                reference_values=reference,
                reference_id="r",
                reference_units="meters",
                target_semantics=TARGET,
            )
        )

    assert fit_quality_warnings(fit((1.0, 3.0, 5.0, 7.0, 9.0, 11.0))) == []
    weak = fit_quality_warnings(fit((5.0, 1.0, 9.0, 0.0, 8.0, 2.0)))
    assert len(weak) == 1 and "Weak calibration" in weak[0]


def test_height_model_gcps_fix_the_ground_plane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Height model + GCPs: ground plane through (elevation - height), scale 1."""
    import numpy as np

    from depthwizard.calibration.apply import apply_calibration
    from depthwizard.calibration.models import CalibrationMethod

    monkeypatch.delenv(DEV_CALIBRATION_ENV, raising=False)
    inspection = inspect_input(make_geotiff(tmp_path / "scene.tif"))
    depth = SyntheticDepthBackend().estimate_depth(inspection)
    h, w = depth.output_resolution.height, depth.output_resolution.width
    heights = np.zeros((h, w))
    heights[1, 2] = 10.0  # one 10 m building; GCPs elsewhere sit on open ground
    depth = depth.model_copy(
        update={
            "depth_values": tuple(float(v) for v in heights.ravel()),
            "preprocessing": {**depth.preprocessing, "height_units": "meters_above_ground"},
        }
    )

    def ground(col: int, row: int) -> float:
        return 100.0 + 2.0 * col + 3.0 * row

    points = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (2, 1)]
    lines = ["pixel_col,pixel_row,elevation"] + [
        f"{c},{r},{ground(c, r) + heights[r, c]}" for c, r in points
    ]
    gcps = tmp_path / "gcps.csv"
    gcps.write_text("\n".join(lines) + "\n")

    result = calibrate_with(select_calibration_provider(str(gcps), TARGET), inspection, depth)
    assert result.method is CalibrationMethod.GCP_GROUND_PLANE
    assert result.scale == 1.0 and result.rmse == pytest.approx(0.0, abs=1e-9)
    dsm = np.asarray(apply_calibration(depth.depth_values, result)).reshape(h, w)
    assert dsm[1, 2] == pytest.approx(ground(2, 1) + 10.0)
    assert dsm[h - 1, 0] == pytest.approx(ground(0, h - 1))
