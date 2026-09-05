"""Transport-neutral local service contract (JSON-safe, versioned).

Pydantic models with wire-friendly shapes only: strings for enum
values, lists (never tuples), explicit optionals, no NumPy, no
callables, no pickle. ``SERVICE_CONTRACT_VERSION`` versions the wire
contract itself — distinct from engine, package and model versions.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.contracts.semantics import ElevationSemantics

#: Wire-contract version (independent of engine/package/model versions).
SERVICE_CONTRACT_VERSION: Literal["1"] = "1"

_METRIC_TARGETS = frozenset(
    {
        ElevationSemantics.HEIGHT_AGL_NDSM,
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    }
)


class ArtifactKind(str, Enum):
    """Artifact types the pipeline can actually produce."""

    DEPTH = "depth"
    CALIBRATION = "calibration"
    HEIGHT = "height"
    DSM = "dsm"
    MESH = "mesh"
    GEOTIFF = "geotiff"


class ServiceRequest(BaseModel):
    """Serializable execution request (no callables, no classes)."""

    model_config = ConfigDict(frozen=True)

    contract_version: Literal["1"] = "1"
    input_path: str = Field(min_length=1)
    target_semantics: ElevationSemantics
    backend: str = Field(
        default="synthetic-depth",
        min_length=1,
        description="Backend identifier. Unknown identifiers are rejected "
        "loudly at execution (no silent fallback).",
    )
    preprocessor: Literal["identity"] = Field(
        default="identity",
        description="Preprocessor identifier (identity only today).",
    )
    build_mesh: bool = False
    geotiff_path: str | None = None
    export_compression: Literal["deflate", "none"] = "deflate"
    export_overwrite: bool = False

    @model_validator(mode="after")
    def _check_request_structure(self) -> ServiceRequest:
        if not self.input_path.strip():
            raise ValueError("input_path must not be blank")
        if self.target_semantics not in _METRIC_TARGETS:
            raise ValueError(
                "service target semantics must be a metric meaning "
                "(height_agl_ndsm, absolute_elevation_dsm)"
            )
        if self.geotiff_path is not None and not self.geotiff_path.strip():
            raise ValueError("geotiff_path must not be blank when provided")
        return self


class ServiceError(BaseModel):
    """Structured service error (domain category preserved)."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(description="Domain error class name, e.g. ModelInferenceError.")
    message: str
    stage: str | None = Field(
        default=None, description="Pipeline state value where failure occurred."
    )


class ArtifactDescriptor(BaseModel):
    """Lightweight artifact summary (metadata-first, no arrays)."""

    model_config = ConfigDict(frozen=True)

    kind: ArtifactKind
    available: bool
    persisted: bool = Field(description="True only for GeoTIFF actually written to disk.")
    path: str | None = Field(default=None, description="Local path (GeoTIFF exports only).")
    semantics: str | None = None
    units: str | None = None
    width: int | None = None
    height: int | None = None
    georeferenced: bool | None = Field(
        default=None, description="True when a CRS-backed frame exists."
    )


class RunSummary(BaseModel):
    """Reproducibility metadata (scalars only, no timestamps)."""

    model_config = ConfigDict(frozen=True)

    input_path: str
    input_checksum: str | None = None
    backend_name: str | None = None
    backend_version: str | None = None
    calibration_method: str | None = None
    calibration_reference: str | None = None
    target_semantics: str | None = None
    mesh_requested: bool = False
    geotiff_path: str | None = None
    engine_version: str


class ServiceResponse(BaseModel):
    """Serializable execution outcome (no arrays, ever)."""

    model_config = ConfigDict(frozen=True)

    contract_version: Literal["1"] = "1"
    success: bool
    final_state: str
    states: list[str]
    failure: ServiceError | None = None
    artifacts: list[ArtifactDescriptor] = Field(default_factory=list)
    summary: RunSummary


class ServiceCapabilities(BaseModel):
    """Factual capability report (no heavy loading to answer)."""

    model_config = ConfigDict(frozen=True)

    contract_version: Literal["1"] = "1"
    supported_input_formats: list[str]
    supported_target_semantics: list[str]
    available_backends: list[str]
    mesh_supported: bool = True
    geotiff_supported: bool = True
