"""Pipeline request and result models (typed, immutable, in-process).

Frozen dataclasses (not Pydantic): requests and results hold live
collaborators and artifact object graphs, not serialization-boundary
data. Static typing is enforced by mypy; instances are immutable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from depthwizard.calibration.models import CalibrationResult
from depthwizard.contracts.artifacts import DepthBackend, DepthResult
from depthwizard.contracts.pipeline import PipelineState
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.dsm.grid import DSMGrid
from depthwizard.export.geotiff import ExportOptions, ExportResult
from depthwizard.height.product import ScientificHeightProduct
from depthwizard.ingestion.models import InputInspection
from depthwizard.mesh.models import TerrainMesh
from depthwizard.pipeline.protocols import (
    CalibrationProvider,
    CancellationToken,
    IdentityPreprocessor,
    Preprocessor,
)
from depthwizard.version import __version__


@dataclass(frozen=True)
class PipelineRequest:
    """Everything a run needs (small explicit configuration)."""

    input_path: str
    backend: DepthBackend
    calibration_provider: CalibrationProvider
    target_semantics: ElevationSemantics
    preprocessor: Preprocessor = field(default_factory=IdentityPreprocessor)
    build_mesh: bool = False
    geotiff_path: str | None = None
    export_options: ExportOptions | None = None
    cancellation: CancellationToken | None = None


@dataclass(frozen=True)
class PipelineFailure:
    """Structured failure record (category preserved, never flattened)."""

    stage: PipelineState
    error_category: str
    message: str


@dataclass(frozen=True)
class PipelineResult:
    """Terminal run outcome with produced artifacts and run metadata.

    Optional artifacts stay None when their stage did not run or did
    not succeed. Large arrays are referenced via held objects, never
    serialized into metadata.
    """

    state: PipelineState
    states: tuple[PipelineState, ...]
    inspection: InputInspection | None = None
    depth: DepthResult | None = None
    calibration: CalibrationResult | None = None
    product: ScientificHeightProduct | None = None
    dsm: DSMGrid | None = None
    mesh: TerrainMesh | None = None
    export: ExportResult | None = None
    failure: PipelineFailure | None = None
    # Reproducibility metadata (scalars only).
    input_path: str = ""
    input_checksum: str | None = None
    backend_name: str | None = None
    backend_version: str | None = None
    calibration_method: str | None = None
    calibration_reference: str | None = None
    calibration_scale: float | None = None
    calibration_offset: float | None = None
    target_semantics: ElevationSemantics | None = None
    mesh_requested: bool = False
    geotiff_path: str | None = None
    engine_version: str = __version__

    @property
    def succeeded(self) -> bool:
        """True only for COMPLETED runs."""
        return self.state is PipelineState.COMPLETED
