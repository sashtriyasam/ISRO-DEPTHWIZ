"""Thin local service over PipelineRunner (translation, not science).

``LocalService`` validates a transport-safe ``ServiceRequest``,
translates it into an internal ``PipelineRequest``, executes exactly
one ``PipelineRunner.run()`` and translates the ``PipelineResult``
into a JSON-safe ``ServiceResponse``. It never calls inference,
rasterization, mesh or export functions directly — the pipeline owns
stage ordering. Synchronous by design; no threads, no sockets.
"""

from __future__ import annotations

from depthwizard.backends.synthetic import SyntheticDepthBackend
from depthwizard.contracts.artifacts import DepthBackend
from depthwizard.contracts.semantics import ElevationSemantics, GeoreferencingLevel
from depthwizard.errors import PipelineExecutionError
from depthwizard.export.geotiff import Compression, ExportOptions
from depthwizard.ingestion.formats import SUPPORTED_SUFFIXES
from depthwizard.pipeline import (
    CalibrationProvider,
    CancellationToken,
    PipelineRequest,
    PipelineResult,
    PipelineRunner,
)
from depthwizard.rdsm.pipeline import run_relative_path
from depthwizard.service.models import (
    SERVICE_CONTRACT_VERSION,
    ArtifactDescriptor,
    ArtifactKind,
    RunSummary,
    ServiceCapabilities,
    ServiceError,
    ServiceRequest,
    ServiceResponse,
)
from depthwizard.version import __version__


def _georeferenced(georeferencing: GeoreferencingLevel) -> bool:
    """Whether a level carries CRS-backed spatial referencing."""
    return georeferencing is not GeoreferencingLevel.NON_GEOREFERENCED


def build_descriptors(result: PipelineResult) -> list[ArtifactDescriptor]:
    """Describe produced artifacts (absent stages stay explicitly absent)."""
    depth = result.depth
    calibration = result.calibration
    product = result.product
    dsm = result.dsm
    mesh = result.mesh
    export = result.export
    descriptors = [
        ArtifactDescriptor(
            kind=ArtifactKind.DEPTH,
            available=depth is not None,
            persisted=False,
            semantics=depth.elevation_semantics.value if depth else None,
            units=depth.units if depth else None,
            width=depth.output_resolution.width if depth else None,
            height=depth.output_resolution.height if depth else None,
            georeferenced=_georeferenced(depth.georeferencing) if depth else None,
        ),
        ArtifactDescriptor(
            kind=ArtifactKind.CALIBRATION,
            available=calibration is not None,
            persisted=False,
            semantics=calibration.target_semantics.value if calibration else None,
            units=calibration.reference_units if calibration else None,
        ),
        ArtifactDescriptor(
            kind=ArtifactKind.HEIGHT,
            available=product is not None,
            persisted=False,
            semantics=product.semantics.value if product else None,
            units=product.units if product else None,
            width=product.width if product else None,
            height=product.height if product else None,
            georeferenced=_georeferenced(product.georeferencing) if product else None,
        ),
        ArtifactDescriptor(
            kind=ArtifactKind.DSM,
            available=dsm is not None,
            persisted=False,
            semantics=dsm.semantics.value if dsm else None,
            units=dsm.units if dsm else None,
            width=dsm.width if dsm else None,
            height=dsm.height if dsm else None,
            georeferenced=_georeferenced(dsm.georeferencing) if dsm else None,
        ),
        ArtifactDescriptor(
            kind=ArtifactKind.MESH,
            available=mesh is not None,
            persisted=False,
            semantics=mesh.semantics.value if mesh else None,
            units=mesh.units if mesh else None,
            width=mesh.width if mesh else None,
            height=mesh.height if mesh else None,
            georeferenced=_georeferenced(mesh.georeferencing) if mesh else None,
        ),
        ArtifactDescriptor(
            kind=ArtifactKind.GEOTIFF,
            available=export is not None,
            persisted=export is not None,
            path=export.path if export else None,
            semantics=dsm.semantics.value if dsm else None,
            units=dsm.units if dsm else None,
            width=export.width if export else None,
            height=export.height if export else None,
            georeferenced=_georeferenced(dsm.georeferencing) if dsm else None,
        ),
    ]
    return descriptors


def build_response(result: PipelineResult) -> ServiceResponse:
    """Translate a pipeline result to the wire response (pure mapping)."""
    failure = result.failure
    return ServiceResponse(
        contract_version=SERVICE_CONTRACT_VERSION,
        success=result.succeeded,
        final_state=result.state.value,
        states=[state.value for state in result.states],
        failure=ServiceError(
            code=failure.error_category,
            message=failure.message,
            stage=failure.stage.value,
        )
        if failure
        else None,
        artifacts=build_descriptors(result),
        summary=RunSummary(
            input_path=result.input_path,
            input_checksum=result.input_checksum,
            backend_name=result.backend_name,
            backend_version=result.backend_version,
            calibration_method=result.calibration_method,
            calibration_reference=result.calibration_reference,
            target_semantics=result.target_semantics.value if result.target_semantics else None,
            mesh_requested=result.mesh_requested,
            geotiff_path=result.geotiff_path,
            engine_version=result.engine_version,
        ),
    )


class LocalService:
    """In-process local service (multi-use; fresh runner per execution)."""

    def __init__(self, backends: dict[str, DepthBackend] | None = None) -> None:
        """Bind backend implementations by identifier.

        Defaults to the deterministic synthetic backend. Overrides let
        embeddings and tests substitute implementations without
        changing the service API; the service still only delegates to
        ``PipelineRunner`` and never calls inference itself.
        """
        self._backends: dict[str, DepthBackend] = (
            dict(backends) if backends is not None else {"synthetic-depth": SyntheticDepthBackend()}
        )

    def capabilities(self) -> ServiceCapabilities:
        """Report factual capabilities (no heavy loading to answer)."""
        return ServiceCapabilities(
            contract_version=SERVICE_CONTRACT_VERSION,
            supported_input_formats=list(SUPPORTED_SUFFIXES),
            supported_target_semantics=[
                ElevationSemantics.HEIGHT_AGL_NDSM.value,
                ElevationSemantics.ABSOLUTE_ELEVATION_DSM.value,
            ],
            available_backends=sorted(self._backends),
        )

    def execute(
        self,
        request: ServiceRequest,
        calibration_provider: CalibrationProvider,
        cancellation: CancellationToken | None = None,
    ) -> ServiceResponse:
        """Validate, translate, run the pipeline, translate the result.

        The calibration provider is an in-process collaborator (no
        serializable provider selection exists yet — real DEM/GCP
        acquisition is a future milestone, and this service fakes no
        calibration source). ``cancellation`` is an optional in-process
        cooperative token observed at pipeline stage boundaries; it is
        not a cross-process mechanism and is never serialized.
        """
        if not isinstance(request, ServiceRequest):
            raise TypeError(
                f"LocalService.execute requires a ServiceRequest; got {type(request).__name__}"
            )
        backend = self._backends.get(request.backend)
        if backend is None:
            raise PipelineExecutionError(f"unknown backend identifier: {request.backend!r}")
        if request.output_mode == "relative":
            return self._execute_relative(request, backend)
        pipeline_request = PipelineRequest(
            input_path=request.input_path,
            backend=backend,
            calibration_provider=calibration_provider,
            target_semantics=request.target_semantics,
            build_mesh=request.build_mesh,
            geotiff_path=request.geotiff_path,
            export_options=ExportOptions(
                overwrite=request.export_overwrite,
                compression=Compression(request.export_compression),
            ),
            cancellation=cancellation,
        )
        result = PipelineRunner().run(pipeline_request)
        return build_response(result)

    def _execute_relative(self, request: ServiceRequest, backend: DepthBackend) -> ServiceResponse:
        """Run the calibration-free rDSM path (no metric output, ever).

        The calibration provider is ignored: relative products must not
        depend on calibration data. Failure modes mirror the pipeline
        path (loud domain errors, no synthetic fallback).
        """
        outcome = run_relative_path(request.input_path, backend)
        depth = outcome.depth
        grid = outcome.grid
        mesh = outcome.mesh
        georeferenced = _georeferenced(depth.georeferencing)
        return ServiceResponse(
            contract_version=SERVICE_CONTRACT_VERSION,
            success=True,
            final_state="completed",
            states=["completed"],
            failure=None,
            artifacts=[
                ArtifactDescriptor(
                    kind=ArtifactKind.DEPTH,
                    available=True,
                    persisted=False,
                    semantics=depth.elevation_semantics.value,
                    units=depth.units,
                    width=depth.output_resolution.width,
                    height=depth.output_resolution.height,
                    georeferenced=georeferenced,
                ),
                ArtifactDescriptor(
                    kind=ArtifactKind.RELATIVE_SURFACE,
                    available=True,
                    persisted=False,
                    semantics=grid.semantics.value,
                    units=grid.units,
                    width=grid.width,
                    height=grid.height,
                    georeferenced=georeferenced,
                ),
                ArtifactDescriptor(
                    kind=ArtifactKind.RELATIVE_MESH,
                    available=True,
                    persisted=False,
                    semantics=mesh.semantics.value,
                    units=mesh.units,
                    width=mesh.width,
                    height=mesh.height,
                    georeferenced=georeferenced,
                ),
            ],
            summary=RunSummary(
                input_path=request.input_path,
                input_checksum=outcome.input_checksum,
                backend_name=depth.model_name,
                backend_version=depth.model_version,
                calibration_method=None,
                calibration_reference=None,
                target_semantics=None,
                mesh_requested=request.build_mesh,
                geotiff_path=None,
                engine_version=__version__,
            ),
        )
