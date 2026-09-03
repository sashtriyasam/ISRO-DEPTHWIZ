"""Failure propagation: stage, category, preserved artifacts, no progress."""

from pathlib import Path

import pytest

from depthwizard.contracts.pipeline import PipelineState
from depthwizard.errors import InvalidInputError
from depthwizard.pipeline import PipelineRunner
from tests.pipeline.support import (
    FailingBackend,
    FailingProvider,
    StripBackend,
    SyntheticCalibrationProvider,
    make_request,
    png_input,
)


def test_input_failure(tmp_path: Path) -> None:
    result = PipelineRunner().run(make_request(str(tmp_path / "missing.png")))
    assert result.state is PipelineState.FAILED
    assert result.states == (PipelineState.FAILED,)
    assert result.failure is not None
    assert result.failure.stage is PipelineState.INPUT_VALIDATED
    assert result.failure.error_category == "InvalidInputError"
    assert result.inspection is None
    assert result.depth is None


def test_unsupported_format_preserved(tmp_path: Path) -> None:
    blob = tmp_path / "blob.bin"
    blob.write_bytes(b"\x00\x01\x02\x03")
    result = PipelineRunner().run(make_request(str(blob)))
    assert result.state is PipelineState.FAILED
    assert result.failure is not None
    assert result.failure.error_category == "UnsupportedFormatError"


def test_inference_failure(tmp_path: Path) -> None:
    result = PipelineRunner().run(make_request(png_input(tmp_path), backend=FailingBackend()))
    assert result.state is PipelineState.FAILED
    assert result.states == (
        PipelineState.INPUT_VALIDATED,
        PipelineState.PREPROCESSING,
        PipelineState.INFERENCE_RUNNING,
        PipelineState.FAILED,
    )
    assert result.failure is not None
    assert result.failure.stage is PipelineState.INFERENCE_RUNNING
    assert result.failure.error_category == "ModelInferenceError"
    assert "boom" in result.failure.message
    assert result.inspection is not None
    assert result.depth is None
    assert result.calibration is None
    assert result.dsm is None
    assert result.mesh is None
    assert result.export is None


def test_calibration_failure(tmp_path: Path) -> None:
    result = PipelineRunner().run(make_request(png_input(tmp_path), provider=FailingProvider()))
    assert result.state is PipelineState.FAILED
    assert result.states[-2:] == (PipelineState.CALIBRATING, PipelineState.FAILED)
    assert result.failure is not None
    assert result.failure.stage is PipelineState.CALIBRATING
    assert result.failure.error_category == "CalibrationError"
    assert result.depth is not None
    assert result.calibration is None
    assert result.dsm is None


def test_contradictory_provider_linkage(tmp_path: Path) -> None:
    provider = SyntheticCalibrationProvider(checksum_override="unrelated-source")
    result = PipelineRunner().run(make_request(png_input(tmp_path), provider=provider))
    assert result.state is PipelineState.FAILED
    assert result.failure is not None
    assert result.failure.stage is PipelineState.CALIBRATING
    assert result.failure.error_category == "CalibrationError"


def test_dsm_failure_propagates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import depthwizard.pipeline.runner as runner_module

    def boom(product: object) -> object:
        raise InvalidInputError("controlled DSM-stage failure")

    monkeypatch.setattr(runner_module, "rasterize_height_product", boom)
    result = PipelineRunner().run(make_request(png_input(tmp_path)))
    assert result.state is PipelineState.FAILED
    assert result.states[-2:] == (PipelineState.DSM_GENERATION, PipelineState.FAILED)
    assert result.failure is not None
    assert result.failure.stage is PipelineState.DSM_GENERATION
    assert result.failure.error_category == "InvalidInputError"
    assert result.product is not None
    assert result.dsm is None
    assert result.mesh is None
    assert result.export is None


def test_mesh_failure_preserves_earlier(tmp_path: Path) -> None:
    result = PipelineRunner().run(
        make_request(png_input(tmp_path), backend=StripBackend(), build_mesh=True)
    )
    assert result.state is PipelineState.FAILED
    assert result.states[-2:] == (PipelineState.MESH_GENERATION, PipelineState.FAILED)
    assert result.failure is not None
    assert result.failure.stage is PipelineState.MESH_GENERATION
    assert result.failure.error_category == "MeshGenerationError"
    assert result.inspection is not None
    assert result.depth is not None
    assert result.calibration is not None
    assert result.product is not None
    assert result.dsm is not None
    assert result.mesh is None
    assert result.export is None


def test_export_failure_preserves_science(tmp_path: Path) -> None:
    target = tmp_path / "out.tif"
    target.write_bytes(b"stale-content")
    result = PipelineRunner().run(
        make_request(png_input(tmp_path), build_mesh=True, geotiff_path=str(target))
    )
    assert result.state is PipelineState.FAILED
    assert result.states[-2:] == (PipelineState.EXPORTING, PipelineState.FAILED)
    assert result.failure is not None
    assert result.failure.stage is PipelineState.EXPORTING
    assert result.failure.error_category == "ExportError"
    assert result.dsm is not None
    assert result.mesh is not None
    assert result.export is None
    assert target.read_bytes() == b"stale-content"
