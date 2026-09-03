"""In-process scientific pipeline orchestration (composition only).

Sequences ingestion, preprocessing, depth inference, calibration,
height semantics, DSM rasterization and optional mesh/export stages
through explicit ``PipelineState`` transitions. The layer owns
sequencing, state, cancellation, failure propagation and run metadata
— never scientific algorithms.
"""

from depthwizard.contracts.pipeline import PipelineState
from depthwizard.errors import PipelineExecutionError
from depthwizard.pipeline.models import (
    PipelineFailure,
    PipelineRequest,
    PipelineResult,
)
from depthwizard.pipeline.protocols import (
    CalibrationProvider,
    CancellationToken,
    IdentityPreprocessor,
    Preprocessor,
)
from depthwizard.pipeline.runner import (
    TRANSITIONS,
    PipelineRunner,
    check_transition,
)

__all__ = [
    "TRANSITIONS",
    "CalibrationProvider",
    "CancellationToken",
    "IdentityPreprocessor",
    "PipelineExecutionError",
    "PipelineFailure",
    "PipelineRequest",
    "PipelineResult",
    "PipelineRunner",
    "PipelineState",
    "Preprocessor",
    "check_transition",
]
