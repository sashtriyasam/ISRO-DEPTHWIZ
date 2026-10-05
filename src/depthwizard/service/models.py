"""Transport-neutral local service contract (JSON-safe, versioned).

Pydantic models with wire-friendly shapes only: strings for enum
values, lists (never tuples), explicit optionals, no NumPy, no
callables, no pickle. ``SERVICE_CONTRACT_VERSION`` versions the wire
contract itself — distinct from engine, package and model versions.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

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
    """Artifact types the service can actually produce."""

    DEPTH = "depth"
    CALIBRATION = "calibration"
    HEIGHT = "height"
    DSM = "dsm"
    MESH = "mesh"
    RELATIVE_SURFACE = "relative_surface"
    RELATIVE_MESH = "relative_mesh"
    GEOTIFF = "geotiff"


class SolarRequestConfig(BaseModel):
    """Optional solar-shadow analysis for a run (angles: both or neither)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sun_elevation_deg: float | None = None
    sun_azimuth_deg: float | None = None
    min_shadow_area_px: int = Field(default=20, ge=1)
    gsd_override: float | None = Field(default=None, gt=0)
    assume_north_up: bool = False


class ServiceRequest(BaseModel):
    """Serializable execution request (no callables, no classes).

    Unknown fields are rejected: silently ignoring them hid that the
    desktop's calibration method, LOD levels and solar settings never
    reached the engine.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

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
    output_mode: Literal["metric", "relative"] = Field(
        default="metric",
        description="Product mode: 'metric' runs the calibrated pipeline, "
        "'relative' runs the calibration-free rDSM path (no metric output).",
    )
    build_mesh: bool = False
    calibration_method: Literal["scale_offset", "scale_offset_huber", "piecewise_linear"] = Field(
        default="scale_offset",
        description="Calibration fitting method for metric runs.",
    )
    calibration_reference_path: str | None = Field(
        default=None,
        description="Local DEM GeoTIFF or GCP CSV backing metric calibration. "
        "Metric runs without one are refused (no fabricated metres).",
    )
    mesh_levels: list[int] | None = Field(
        default=None,
        description="Mesh LOD factors (each >= 1); the first is the returned mesh.",
    )
    include_payload: bool = Field(
        default=False,
        description="Return the terrain/relative product of this run in the "
        "response so the desktop needs no second inference pass.",
    )
    solar_config: SolarRequestConfig | None = None
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
        if self.calibration_reference_path is not None and not (
            self.calibration_reference_path.strip()
        ):
            raise ValueError("calibration_reference_path must not be blank when provided")
        if self.mesh_levels is not None and (
            not self.mesh_levels or any(level < 1 for level in self.mesh_levels)
        ):
            raise ValueError("mesh_levels must be a non-empty list of factors >= 1")
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
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal findings (weak calibration fit, flat depth, ...).",
    )
    solar: dict[str, Any] | None = Field(
        default=None,
        description="Solar-shadow height cues of this run (independent cross-check; "
        "never fused into the DSM), or why the analysis was refused.",
    )
    payload: dict[str, Any] | None = Field(
        default=None,
        description="Terrain or relative product JSON of this very run "
        "(only when include_payload was requested and the run succeeded).",
    )


class ServiceCapabilities(BaseModel):
    """Factual capability report (no heavy loading to answer)."""

    model_config = ConfigDict(frozen=True)

    contract_version: Literal["1"] = "1"
    supported_input_formats: list[str]
    supported_target_semantics: list[str]
    available_backends: list[str]
    mesh_supported: bool = True
    geotiff_supported: bool = True
