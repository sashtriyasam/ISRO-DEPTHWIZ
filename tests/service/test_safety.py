"""Failure mapping, cancellation, agnosticism, client-safe errors."""

from pathlib import Path
from typing import Any

import pytest

from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.errors import PipelineExecutionError
from depthwizard.pipeline import CancellationToken
from depthwizard.service import LocalService, ServiceRequest
from tests.pipeline.support import (
    CancellingProvider,
    FailingBackend,
    FailingProvider,
    SyntheticCalibrationProvider,
    png_input,
)


def _request(input_path: str, **overrides: Any) -> ServiceRequest:
    base: dict[str, Any] = {
        "input_path": input_path,
        "target_semantics": ElevationSemantics.HEIGHT_AGL_NDSM,
    }
    base.update(overrides)
    return ServiceRequest(**base)


def test_invalid_input_mapped(tmp_path: Path) -> None:
    response = LocalService().execute(
        _request(str(tmp_path / "missing.png")), SyntheticCalibrationProvider()
    )
    assert response.success is False
    assert response.final_state == "failed"
    assert response.failure is not None
    assert response.failure.code == "InvalidInputError"
    assert response.failure.stage == "input_validated"
    assert "missing.png" in response.failure.message


def test_inference_failure_mapped(tmp_path: Path) -> None:
    service = LocalService(backends={"synthetic-depth": FailingBackend()})
    response = service.execute(_request(png_input(tmp_path)), SyntheticCalibrationProvider())
    assert response.success is False
    assert response.failure is not None
    assert response.failure.code == "ModelInferenceError"
    assert response.failure.stage == "inference_running"
    by_kind = {artifact.kind.value: artifact for artifact in response.artifacts}
    assert by_kind["depth"].available is False
    assert by_kind["dsm"].available is False


def test_calibration_failure_mapped(tmp_path: Path) -> None:
    response = LocalService().execute(_request(png_input(tmp_path)), FailingProvider())
    assert response.success is False
    assert response.failure is not None
    assert response.failure.code == "CalibrationError"
    assert response.failure.stage == "calibrating"


def test_export_failure_mapped(tmp_path: Path) -> None:
    target = tmp_path / "out.tif"
    target.write_bytes(b"stale-content")
    response = LocalService().execute(
        _request(png_input(tmp_path), geotiff_path=str(target)),
        SyntheticCalibrationProvider(),
    )
    assert response.success is False
    assert response.failure is not None
    assert response.failure.code == "ExportError"
    assert response.failure.stage == "exporting"
    by_kind = {artifact.kind.value: artifact for artifact in response.artifacts}
    assert by_kind["dsm"].available is True
    assert by_kind["geotiff"].available is False


def test_precancelled_request(tmp_path: Path) -> None:
    token = CancellationToken()
    token.cancel()
    service = LocalService()
    request = _request(png_input(tmp_path))
    response = service.execute(request, SyntheticCalibrationProvider(), cancellation=token)
    assert response.success is False
    assert response.final_state == "cancelled"
    assert response.states == ["cancelled"]
    by_kind = {artifact.kind.value: artifact for artifact in response.artifacts}
    assert all(not artifact.available for artifact in by_kind.values())


def test_midrun_cancellation(tmp_path: Path) -> None:
    token = CancellationToken()
    response = LocalService().execute(
        _request(png_input(tmp_path)),
        CancellingProvider(token),
        cancellation=token,
    )
    assert response.success is False
    assert response.final_state == "cancelled"
    assert response.states[-1] == "cancelled"
    assert "completed" not in response.states
    by_kind = {artifact.kind.value: artifact for artifact in response.artifacts}
    assert by_kind["calibration"].available is True
    assert by_kind["dsm"].available is False


def test_unknown_backend_rejected(tmp_path: Path) -> None:
    service = LocalService(backends={})
    with pytest.raises(PipelineExecutionError, match="unknown backend"):
        service.execute(_request(png_input(tmp_path)), SyntheticCalibrationProvider())


def test_client_safe_errors(tmp_path: Path) -> None:
    response = LocalService().execute(
        _request(str(tmp_path / "missing.png")), SyntheticCalibrationProvider()
    )
    assert response.failure is not None
    assert "Traceback" not in response.failure.message
    assert ".py" not in response.failure.message
    assert str(tmp_path) not in response.failure.message
