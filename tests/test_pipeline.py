"""Deterministic tests for the pipeline state contract."""

from depthwizard.contracts.pipeline import PipelineState


def test_pipeline_states_enumerable_and_explicit() -> None:
    assert len(list(PipelineState)) == 11
    assert PipelineState("input_validated") is PipelineState.INPUT_VALIDATED
    assert PipelineState("solar_shadow_analysis") is PipelineState.SOLAR_SHADOW_ANALYSIS
    assert PipelineState("completed") is PipelineState.COMPLETED


def test_terminal_states() -> None:
    assert PipelineState.terminal_states() == frozenset(
        {
            PipelineState.COMPLETED,
            PipelineState.FAILED,
            PipelineState.CANCELLED,
        }
    )
    assert PipelineState.INFERENCE_RUNNING not in PipelineState.terminal_states()
