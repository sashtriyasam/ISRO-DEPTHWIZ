"""JSON-safe desktop transport models (field-for-field with the wire).

Shapes mirror the desktop artifact contract (BackendDepthResult /
BackendCalibrationResult / BackendTerrainProduct): strings for enums,
lists never tuples, explicit optionals, NaN/inf never emitted. NumPy
values become plain Python scalars; datetime becomes ISO text.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from depthwizard.errors import InvalidInputError


class TransportResolution(BaseModel):
    """Pixel dimensions."""

    model_config = ConfigDict(frozen=True)

    width: int
    height: int


class TransportAffine(BaseModel):
    """GDAL-order affine (a, b, c, d, e, f)."""

    model_config = ConfigDict(frozen=True)

    a: float
    b: float
    c: float
    d: float
    e: float
    f: float


class TransportBounds(BaseModel):
    """Axis-aligned bounds."""

    model_config = ConfigDict(frozen=True)

    min_x: float
    min_y: float
    max_x: float
    max_y: float


class TransportSpatialDetails(BaseModel):
    """Spatial details with explicit nulls (never invented values)."""

    model_config = ConfigDict(frozen=True)

    crs: str | None = None
    transform: TransportAffine | None = None
    bounds: TransportBounds | None = None
    pixel_width: int | None = None
    pixel_height: int | None = None
    resolution_gsd: float | None = None
    nodata: float | None = None
    units: str | None = None
    raster_width: int | None = None
    raster_height: int | None = None
    source: str | None = None


class TransportSpatialContext(BaseModel):
    """Spatial presence wrapper."""

    model_config = ConfigDict(frozen=True)

    kind: str
    details: TransportSpatialDetails | None = None


class TransportProvenance(BaseModel):
    """Compact provenance (datetimes as ISO text, never objects)."""

    model_config = ConfigDict(frozen=True)

    source_input_id: str | None = None
    input_checksum: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    checkpoint_id: str | None = None
    calibration_method: str | None = None
    calibration_reference: str | None = None
    calibration_params: list[float] | None = None
    software_version: str | None = None
    code_commit: str | None = None
    generated_at: str | None = None
    units: str | None = None
    semantic_meaning: str | None = None


class TransportDepthResult(BaseModel):
    """Wire form of a depth result (values stay relative when relative)."""

    model_config = ConfigDict(frozen=True)

    model_name: str
    model_version: str | None = None
    checkpoint_id: str | None = None
    input_resolution: TransportResolution
    output_resolution: TransportResolution
    depth_scale: str
    elevation_semantics: str
    georeferencing: str
    depth_values: list[float]
    confidence_values: list[float] | None = None
    valid_mask: list[bool] | None = None
    preprocessing: dict[str, str] = Field(default_factory=dict)
    units: str | None = None
    spatial: TransportSpatialContext
    provenance: TransportProvenance | None = None


class TransportCalibrationResult(BaseModel):
    """Wire form of a fitted calibration."""

    model_config = ConfigDict(frozen=True)

    method: str
    scale: float
    offset: float
    reference_id: str
    reference_checksum: str | None = None
    reference_units: str
    target_semantics: str
    total_samples: int
    valid_samples: int
    rmse: float
    mae: float
    max_abs_residual: float
    r_squared: float
    engine_version: str
    source_input_id: str | None = None
    source_checksum: str | None = None


class TransportDsm(BaseModel):
    """Wire form of a one-band DSM (invalid pixels are null, never NaN)."""

    model_config = ConfigDict(frozen=True)

    width: int
    height: int
    dtype: str
    units: str
    semantics: str
    values: list[float | None]
    valid_mask: list[bool]
    invalid_count: int
    nodata: float | None = None
    georeferencing: str
    spatial: TransportSpatialContext


class TransportMesh(BaseModel):
    """Wire form of a terrain mesh (finite arrays only)."""

    model_config = ConfigDict(frozen=True)

    vertices: list[float]
    indices: list[int]
    normals: list[float]
    uvs: list[float]
    vertex_source_indices: list[int]
    vertex_count: int
    triangle_count: int
    valid_source_pixels: int
    invalid_source_pixels: int
    skipped_cells: int
    coverage: float
    frame: str
    origin_x: float | None = None
    origin_y: float | None = None
    width: int
    height: int
    units: str
    semantics: str
    georeferencing: str
    spatial: TransportSpatialContext
    depth_model_name: str
    depth_model_version: str | None = None
    depth_checkpoint_id: str | None = None
    source_input_id: str | None = None
    source_checksum: str | None = None
    calibration_method: str
    calibration_reference: str
    calibration_scale: float
    calibration_offset: float
    calibration_valid_samples: int
    provenance: TransportProvenance | None = None


class TransportTerrainProduct(BaseModel):
    """Wire form of the depth+DSM+mesh terrain bundle."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["terrain"] = "terrain"
    depth_result: TransportDepthResult
    dsm: TransportDsm
    mesh: TransportMesh


class TransportFailure(BaseModel):
    """Wire failure record (category preserved)."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    stage: str | None = None


class TransportBundle(BaseModel):
    """Client-facing pipeline bundle (lightweight, JSON-safe)."""

    model_config = ConfigDict(frozen=True)

    status: str
    states: list[str] = Field(default_factory=list)
    failure: TransportFailure | None = None
    depth: TransportDepthResult | None = None
    calibration: TransportCalibrationResult | None = None
    dsm: TransportDsm | None = None
    mesh: TransportMesh | None = None
    geotiff_path: str | None = None
    artifacts_available: list[str] = Field(default_factory=list)


def _finite_or_reject(values: list[float], field: str) -> list[float]:
    """Reject non-finite mesh coordinates (DSM NaN has its own null rule)."""
    for index, value in enumerate(values):
        if not math.isfinite(value):
            raise InvalidInputError(f"{field}[{index}] must be finite for transport")
    return values


def _isoformat(value: datetime | None) -> str | None:
    """Datetime to ISO text (None stays None)."""
    return value.isoformat() if value is not None else None


def _provenance(provenance: Any) -> TransportProvenance | None:
    """Map a product provenance record (or pass None through)."""
    if provenance is None:
        return None
    params = provenance.calibration_params
    return TransportProvenance(
        source_input_id=provenance.source_input_id,
        input_checksum=provenance.input_checksum,
        model_name=provenance.model_name,
        model_version=provenance.model_version,
        checkpoint_id=provenance.checkpoint_id,
        calibration_method=provenance.calibration_method,
        calibration_reference=provenance.calibration_reference,
        calibration_params=[float(p) for p in params] if params is not None else None,
        software_version=provenance.software_version,
        code_commit=provenance.code_commit,
        generated_at=_isoformat(provenance.generated_at),
        units=provenance.units,
        semantic_meaning=provenance.semantic_meaning,
    )


def _spatial(context: Any) -> TransportSpatialContext:
    """Map a spatial context (details preserved, never invented)."""
    details = context.details
    return TransportSpatialContext(
        kind=context.kind.value,
        details=TransportSpatialDetails(
            crs=details.crs,
            transform=TransportAffine(
                a=details.transform.a,
                b=details.transform.b,
                c=details.transform.c,
                d=details.transform.d,
                e=details.transform.e,
                f=details.transform.f,
            )
            if details.transform is not None
            else None,
            bounds=TransportBounds(
                min_x=details.bounds.min_x,
                min_y=details.bounds.min_y,
                max_x=details.bounds.max_x,
                max_y=details.bounds.max_y,
            )
            if details.bounds is not None
            else None,
            pixel_width=details.pixel_width,
            pixel_height=details.pixel_height,
            resolution_gsd=details.resolution_gsd,
            nodata=details.nodata,
            units=details.units,
            raster_width=details.raster_width,
            raster_height=details.raster_height,
            source=details.source,
        )
        if details is not None
        else None,
    )
