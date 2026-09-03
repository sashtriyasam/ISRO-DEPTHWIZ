"""Single-run pipeline orchestration (composition, not science).

``PipelineRunner`` sequences existing subsystems through explicit
``PipelineState`` transitions with stage-scoped failure capture,
cooperative cancellation and artifact preservation. Each runner
instance executes at most one run. No threads, no async, no caching,
no logging framework: deterministic state history plus structured
failure data is the observability.
"""

from __future__ import annotations

import math
from pathlib import Path

from depthwizard.calibration.models import CalibrationResult
from depthwizard.contracts.artifacts import METRIC_UNIT, DepthResult
from depthwizard.contracts.pipeline import PipelineState
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.dsm.grid import DSMGrid
from depthwizard.dsm.rasterize import rasterize_height_product
from depthwizard.errors import CalibrationError, PipelineExecutionError
from depthwizard.export.geotiff import ExportResult, export_geotiff
from depthwizard.height.factory import create_scientific_height_product
from depthwizard.height.product import ScientificHeightProduct
from depthwizard.ingestion.api import inspect_input
from depthwizard.ingestion.models import InputInspection
from depthwizard.mesh.build import build_terrain_mesh
from depthwizard.mesh.models import TerrainMesh
from depthwizard.pipeline.models import (
    PipelineFailure,
    PipelineRequest,
    PipelineResult,
)
from depthwizard.version import __version__

#: Explicit legal transitions. Terminal states have no outgoing edges.
TRANSITIONS: dict[PipelineState, frozenset[PipelineState]] = {
    PipelineState.INPUT_VALIDATED: frozenset(
        {PipelineState.PREPROCESSING, PipelineState.FAILED, PipelineState.CANCELLED}
    ),
    PipelineState.PREPROCESSING: frozenset(
        {PipelineState.INFERENCE_RUNNING, PipelineState.FAILED, PipelineState.CANCELLED}
    ),
    PipelineState.INFERENCE_RUNNING: frozenset(
        {PipelineState.CALIBRATING, PipelineState.FAILED, PipelineState.CANCELLED}
    ),
    PipelineState.CALIBRATING: frozenset(
        {PipelineState.DSM_GENERATION, PipelineState.FAILED, PipelineState.CANCELLED}
    ),
    PipelineState.DSM_GENERATION: frozenset(
        {
            PipelineState.MESH_GENERATION,
            PipelineState.EXPORTING,
            PipelineState.COMPLETED,
            PipelineState.FAILED,
            PipelineState.CANCELLED,
        }
    ),
    PipelineState.MESH_GENERATION: frozenset(
        {
            PipelineState.EXPORTING,
            PipelineState.COMPLETED,
            PipelineState.FAILED,
            PipelineState.CANCELLED,
        }
    ),
    PipelineState.EXPORTING: frozenset(
        {PipelineState.COMPLETED, PipelineState.FAILED, PipelineState.CANCELLED}
    ),
    PipelineState.COMPLETED: frozenset(),
    PipelineState.FAILED: frozenset(),
    PipelineState.CANCELLED: frozenset(),
}

_METRIC_TARGETS = frozenset(
    {
        ElevationSemantics.HEIGHT_AGL_NDSM,
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    }
)


def check_transition(current: PipelineState, nxt: PipelineState) -> None:
    """Validate one state transition (raises on illegal moves)."""
    if nxt not in TRANSITIONS[current]:
        raise PipelineExecutionError(f"illegal pipeline transition: {current.value} -> {nxt.value}")


class PipelineRunner:
    """Single-use in-process pipeline runner."""

    def __init__(self) -> None:
        """Create an unstarted runner."""
        self._used = False

    def run(self, request: PipelineRequest) -> PipelineResult:
        """Execute one run (each instance runs at most once)."""
        if self._used:
            raise PipelineExecutionError(
                "PipelineRunner instances are single-use; create a new runner per run"
            )
        self._used = True
        engine = _Engine(request)
        return engine.execute()


class _Engine:
    """Mutable per-run execution context (internal, never shared)."""

    def __init__(self, request: PipelineRequest) -> None:
        """Capture the request and empty artifact slots."""
        self._request = request
        self._states: list[PipelineState] = []
        self._inspection: InputInspection | None = None
        self._depth: DepthResult | None = None
        self._calibration: CalibrationResult | None = None
        self._product: ScientificHeightProduct | None = None
        self._dsm: DSMGrid | None = None
        self._mesh: TerrainMesh | None = None
        self._export: ExportResult | None = None

    def _enter(self, state: PipelineState) -> None:
        """Record a transition (bootstrap allows terminal states first).

        A run opens with INPUT_VALIDATED after real inspection, but
        FAILED (inspection never succeeded) and CANCELLED (cancelled
        before start) are legitimate first records. Any other opening
        state would falsely claim work happened.
        """
        if not self._states:
            if state not in (
                PipelineState.INPUT_VALIDATED,
                PipelineState.FAILED,
                PipelineState.CANCELLED,
            ):
                raise PipelineExecutionError(
                    f"runs must open with INPUT_VALIDATED, not {state.value}"
                )
        else:
            check_transition(self._states[-1], state)
        self._states.append(state)

    def _cancelled(self) -> bool:
        """Whether the request token asks for cancellation."""
        token = self._request.cancellation
        return token is not None and token.is_cancelled

    def _finish(
        self, state: PipelineState, failure: PipelineFailure | None = None
    ) -> PipelineResult:
        """Build the terminal result preserving produced artifacts."""
        self._enter(state)
        request = self._request
        calibration = self._calibration
        return PipelineResult(
            state=state,
            states=tuple(self._states),
            inspection=self._inspection,
            depth=self._depth,
            calibration=calibration,
            product=self._product,
            dsm=self._dsm,
            mesh=self._mesh,
            export=self._export,
            failure=failure,
            input_path=request.input_path,
            input_checksum=(self._inspection.handle.sha256 if self._inspection else None),
            backend_name=request.backend.model_name,
            backend_version=request.backend.model_version,
            calibration_method=(calibration.method.value if calibration else None),
            calibration_reference=(calibration.reference_id if calibration else None),
            calibration_scale=calibration.scale if calibration else None,
            calibration_offset=calibration.offset if calibration else None,
            target_semantics=request.target_semantics,
            mesh_requested=request.build_mesh,
            geotiff_path=request.geotiff_path,
            engine_version=__version__,
        )

    def _fail(self, stage: PipelineState, exc: BaseException) -> PipelineResult:
        """Record a stage failure, preserving earlier artifacts."""
        return self._finish(
            PipelineState.FAILED,
            PipelineFailure(
                stage=stage,
                error_category=type(exc).__name__,
                message=str(exc) or type(exc).__name__,
            ),
        )

    def execute(self) -> PipelineResult:
        """Run every requested stage in dependency order."""
        request = self._request
        if self._cancelled():
            return self._finish(PipelineState.CANCELLED)
        try:
            inspection = inspect_input(request.input_path)
        except Exception as exc:
            return self._fail(PipelineState.INPUT_VALIDATED, exc)
        self._inspection = inspection
        self._enter(PipelineState.INPUT_VALIDATED)

        if self._cancelled():
            return self._finish(PipelineState.CANCELLED)
        self._enter(PipelineState.PREPROCESSING)
        try:
            prepared = request.preprocessor.prepare(inspection)
        except Exception as exc:
            return self._fail(PipelineState.PREPROCESSING, exc)
        if not isinstance(prepared, InputInspection):
            return self._fail(
                PipelineState.PREPROCESSING,
                PipelineExecutionError(
                    f"preprocessor {request.preprocessor.name!r} must return "
                    f"InputInspection, got {type(prepared).__name__}"
                ),
            )

        if self._cancelled():
            return self._finish(PipelineState.CANCELLED)
        self._enter(PipelineState.INFERENCE_RUNNING)
        try:
            depth = request.backend.estimate_depth(prepared)
        except Exception as exc:
            return self._fail(PipelineState.INFERENCE_RUNNING, exc)
        if not isinstance(depth, DepthResult):
            return self._fail(
                PipelineState.INFERENCE_RUNNING,
                PipelineExecutionError(
                    f"backend {request.backend.model_name!r} must return "
                    f"DepthResult, got {type(depth).__name__}"
                ),
            )
        self._depth = depth

        if self._cancelled():
            return self._finish(PipelineState.CANCELLED)
        self._enter(PipelineState.CALIBRATING)
        try:
            calibration = request.calibration_provider.calibrate(depth)
            self._check_calibration(calibration)
            product = create_scientific_height_product(depth, calibration, request.target_semantics)
        except Exception as exc:
            return self._fail(PipelineState.CALIBRATING, exc)
        self._calibration = calibration
        self._product = product

        if self._cancelled():
            return self._finish(PipelineState.CANCELLED)
        self._enter(PipelineState.DSM_GENERATION)
        try:
            dsm = rasterize_height_product(product)
        except Exception as exc:
            return self._fail(PipelineState.DSM_GENERATION, exc)
        self._dsm = dsm

        if request.build_mesh:
            if self._cancelled():
                return self._finish(PipelineState.CANCELLED)
            self._enter(PipelineState.MESH_GENERATION)
            try:
                mesh = build_terrain_mesh(dsm)
            except Exception as exc:
                return self._fail(PipelineState.MESH_GENERATION, exc)
            self._mesh = mesh

        if request.geotiff_path is not None:
            if self._cancelled():
                return self._finish(PipelineState.CANCELLED)
            self._enter(PipelineState.EXPORTING)
            try:
                export = export_geotiff(dsm, Path(request.geotiff_path), request.export_options)
            except Exception as exc:
                return self._fail(PipelineState.EXPORTING, exc)
            self._export = export

        return self._finish(PipelineState.COMPLETED)

    def _check_calibration(self, calibration: CalibrationResult) -> None:
        """Verify provider output before height semantics (no refitting)."""
        request = self._request
        if not isinstance(calibration, CalibrationResult):
            raise PipelineExecutionError(
                f"provider {request.calibration_provider.name!r} must return "
                f"CalibrationResult, got {type(calibration).__name__}"
            )
        if not math.isfinite(calibration.scale) or not math.isfinite(calibration.offset):
            raise CalibrationError(
                f"provider returned non-finite parameters: "
                f"scale={calibration.scale!r}, offset={calibration.offset!r}"
            )
        if calibration.target_semantics not in _METRIC_TARGETS:
            raise CalibrationError(
                "provider calibration target must be a metric meaning; "
                f"got '{calibration.target_semantics.value}'"
            )
        if calibration.reference_units != METRIC_UNIT:
            raise CalibrationError(
                "provider calibration reference must carry explicit metric "
                f"units ('{METRIC_UNIT}'); got '{calibration.reference_units}'"
            )
        if calibration.target_semantics is not request.target_semantics:
            raise CalibrationError(
                f"request target '{request.target_semantics.value}' disagrees "
                f"with provider target '{calibration.target_semantics.value}'; "
                "refusing to override calibration semantics"
            )
        source_checksum = calibration.source_checksum
        depth_checksum = self._depth.provenance.input_checksum if self._depth is not None else None
        if (
            source_checksum is not None
            and depth_checksum is not None
            and source_checksum != depth_checksum
        ):
            raise CalibrationError(
                "provider calibration source contradicts the depth input "
                "(checksums differ); refusing to combine unrelated sources"
            )
