"""Cancellation at stage boundaries (synchronous, cooperative)."""

from pathlib import Path

import pytest

from depthwizard.contracts.pipeline import PipelineState
from depthwizard.errors import PipelineExecutionError
from depthwizard.pipeline import CancellationToken, PipelineRunner, check_transition
from tests.pipeline.support import CancellingProvider, make_request, png_input


def test_cancel_after_calibration(tmp_path: Path) -> None:
    token = CancellationToken()
    request = make_request(
        png_input(tmp_path),
        provider=CancellingProvider(token),
        build_mesh=True,
        geotiff_path=str(tmp_path / "out.tif"),
        token=token,
    )
    result = PipelineRunner().run(request)
    assert result.state is PipelineState.CANCELLED
    assert result.states == (
        PipelineState.INPUT_VALIDATED,
        PipelineState.PREPROCESSING,
        PipelineState.INFERENCE_RUNNING,
        PipelineState.CALIBRATING,
        PipelineState.CANCELLED,
    )
    assert PipelineState.COMPLETED not in result.states
    # Completed work survives; later stages never execute.
    assert result.calibration is not None
    assert result.dsm is None
    assert result.mesh is None
    assert result.export is None
    assert result.failure is None
    assert not (tmp_path / "out.tif").exists()


def test_precancelled_token(tmp_path: Path) -> None:
    token = CancellationToken()
    token.cancel()
    result = PipelineRunner().run(make_request(png_input(tmp_path), token=token))
    assert result.state is PipelineState.CANCELLED
    assert result.states == (PipelineState.CANCELLED,)
    assert result.inspection is None
    assert token.is_cancelled


def test_token_defaults_uncancelled() -> None:
    token = CancellationToken()
    assert token.is_cancelled is False
    token.cancel()
    token.cancel()
    assert token.is_cancelled is True


def test_transition_table() -> None:
    # Legal moves pass silently.
    check_transition(PipelineState.INPUT_VALIDATED, PipelineState.PREPROCESSING)
    check_transition(PipelineState.DSM_GENERATION, PipelineState.COMPLETED)
    check_transition(PipelineState.DSM_GENERATION, PipelineState.MESH_GENERATION)
    check_transition(PipelineState.MESH_GENERATION, PipelineState.EXPORTING)
    check_transition(PipelineState.EXPORTING, PipelineState.COMPLETED)
    check_transition(PipelineState.INFERENCE_RUNNING, PipelineState.FAILED)
    # Illegal moves raise.
    illegal = [
        (PipelineState.FAILED, PipelineState.COMPLETED),
        (PipelineState.CANCELLED, PipelineState.COMPLETED),
        (PipelineState.COMPLETED, PipelineState.INFERENCE_RUNNING),
        (PipelineState.INPUT_VALIDATED, PipelineState.EXPORTING),
        (PipelineState.INFERENCE_RUNNING, PipelineState.EXPORTING),
        (PipelineState.CALIBRATING, PipelineState.COMPLETED),
        (PipelineState.INPUT_VALIDATED, PipelineState.INPUT_VALIDATED),
    ]
    for current, nxt in illegal:
        with pytest.raises(PipelineExecutionError, match="illegal pipeline transition"):
            check_transition(current, nxt)
