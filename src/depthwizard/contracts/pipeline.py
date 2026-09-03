"""Future pipeline state model (states only, no engine).

Lists the states a later orchestration layer may move through.
No execution, no async machinery, no fake progress is implemented here.
"""

from __future__ import annotations

from enum import Enum


class PipelineState(str, Enum):
    """Typed pipeline states for future orchestration."""

    INPUT_VALIDATED = "input_validated"
    PREPROCESSING = "preprocessing"
    INFERENCE_RUNNING = "inference_running"
    CALIBRATING = "calibrating"
    DSM_GENERATION = "dsm_generation"
    MESH_GENERATION = "mesh_generation"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @classmethod
    def terminal_states(cls) -> frozenset[PipelineState]:
        """States after which no further transitions are expected."""
        return frozenset({cls.COMPLETED, cls.FAILED, cls.CANCELLED})
