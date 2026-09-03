"""Pipeline collaborator protocols and default implementations.

Small typed boundaries for the two genuinely replaceable collaborators:
input preprocessing (identity today, scientific stages later) and
calibration-reference acquisition (injected: DEM/GCP/benchmark sources
live outside orchestration). Everything else calls existing subsystem
APIs directly — no generic plugin framework.
"""

from __future__ import annotations

from typing import Protocol

from depthwizard.calibration.models import CalibrationResult
from depthwizard.contracts.artifacts import DepthResult
from depthwizard.ingestion.models import InputInspection


class Preprocessor(Protocol):
    """Input preparation boundary (validated inspection in/out)."""

    @property
    def name(self) -> str:
        """Stable preprocessor name for run metadata."""
        ...

    def prepare(self, inspection: InputInspection) -> InputInspection:
        """Prepare a validated inspection for inference."""
        ...


class IdentityPreprocessor:
    """Default deterministic no-op preprocessor.

    Returns the inspection unchanged. The name records explicitly that
    no transformation (resize/normalize/crop/augment) was applied.
    """

    @property
    def name(self) -> str:
        """Preprocessor name."""
        return "identity"

    def prepare(self, inspection: InputInspection) -> InputInspection:
        """Return the inspection unchanged."""
        return inspection


class CalibrationProvider(Protocol):
    """Metric-reference acquisition boundary (injected, source-agnostic).

    Orchestration never knows whether references come from a DEM,
    GCPs, paired benchmark data or another future subsystem. The
    provider returns an already-validated ``CalibrationResult``.
    """

    @property
    def name(self) -> str:
        """Stable provider name for run metadata."""
        ...

    def calibrate(self, depth_result: DepthResult) -> CalibrationResult:
        """Acquire references and fit the calibration for a depth result."""
        ...


class CancellationToken:
    """Lightweight cooperative cancellation control (synchronous).

    Providers or stage callbacks call :meth:`cancel`; the runner
    observes it at stage boundaries. No threads, no async.
    """

    def __init__(self) -> None:
        """Create an uncancelled token."""
        self._cancelled = False

    @property
    def is_cancelled(self) -> bool:
        """Whether cancellation has been requested."""
        return self._cancelled

    def cancel(self) -> None:
        """Request cancellation (idempotent)."""
        self._cancelled = True
