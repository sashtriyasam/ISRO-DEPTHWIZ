"""DEM inspection and terrain-reference contracts (immutable, typed).

``DEMInspection`` describes a validated local DEM source (metadata
only — no array storage). ``TerrainReferenceGrid`` is the owned,
aligned terrain-elevation grid: ground reference, never a surface
model. ``TerrainSample`` is the typed sampling outcome. None of these
construct calibration objects or mutate sources.
"""

from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.contracts.spatial import AffineTransform, Bounds
from depthwizard.geospatial.warp import ResamplingMethod
from depthwizard.ingestion.formats import DetectedFormat
from depthwizard.ingestion.models import InspectionStatus


class DEMInspection(BaseModel):
    """Validated local DEM source description (metadata only)."""

    model_config = ConfigDict(frozen=True)

    source_path: str = Field(description="Path as supplied (not absolutised).")
    display_name: str = Field(description="Basename for diagnostics.")
    file_size: int = Field(gt=0)
    sha256: str = Field(min_length=64, max_length=64)
    detected_format: DetectedFormat = Field(description="TIFF only this milestone.")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    band_count: int = Field(description="Always 1: single elevation band.")
    dtype: str = Field(description="Rasterio dtype name, e.g. 'float32'.")
    nodata: float | None = Field(default=None, description="Source nodata marker, if declared.")
    crs: str = Field(min_length=1, description="CRS identifier (mandatory).")
    transform: AffineTransform
    bounds: Bounds
    resolution: float | None = Field(
        default=None, gt=0, description="Ground sampling distance, when square."
    )
    vertical_units: str = Field(description="Explicit metric units ('meters').")
    vertical_semantics: ElevationSemantics = Field(
        description="Always TERRAIN_ELEVATION for DEM sources."
    )
    source_format_metadata: dict[str, str] = Field(default_factory=dict)
    status: InspectionStatus = InspectionStatus.VALID

    @model_validator(mode="after")
    def _check_dem_honesty(self) -> DEMInspection:
        if self.detected_format is not DetectedFormat.TIFF:
            raise ValueError("DEM sources must be GeoTIFF this milestone")
        if self.band_count != 1:
            raise ValueError("DEM sources must carry a single elevation band")
        if self.vertical_units != "meters":
            raise ValueError("DEM vertical units must be explicit 'meters'")
        if self.vertical_semantics is not ElevationSemantics.TERRAIN_ELEVATION:
            raise ValueError("DEM sources carry terrain elevation, never DSM/AGL meaning")
        return self


class TerrainReferenceGrid(BaseModel):
    """Owned aligned terrain-elevation reference (ground, not surface).

    Controlled immutability like DSMGrid: frozen model, freshly
    allocated arrays, consumers treat arrays as read-only.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    array: np.ndarray = Field(description="2D float array, shape (height, width).")
    valid_mask: np.ndarray = Field(description="2D bool array, True marks valid terrain.")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    dtype: str = Field(description="Storage dtype name ('float32'/'float64').")
    units: str = Field(description="Always explicit metric units ('meters').")
    semantics: ElevationSemantics = Field(description="Always TERRAIN_ELEVATION.")
    nodata: float = Field(description="Documented nodata marker (NaN).")
    invalid_count: int = Field(ge=0)
    crs: str = Field(min_length=1, description="Grid CRS identifier.")
    transform: AffineTransform
    bounds: Bounds
    resolution: float | None = Field(default=None, gt=0)
    source_dem_id: str = Field(min_length=1)
    source_checksum: str = Field(min_length=64, max_length=64)
    source_crs: str = Field(min_length=1)
    source_resolution: float | None = Field(default=None, gt=0)
    target_resolution: float | None = Field(default=None, gt=0)
    resampling: ResamplingMethod | None = Field(
        default=None,
        description="Warp method used; None means native grid, no resampling applied.",
    )
    provenance: ProductProvenance = Field(description="Reused product provenance.")

    @model_validator(mode="after")
    def _check_terrain_honesty(self) -> TerrainReferenceGrid:
        if self.units != "meters":
            raise ValueError("terrain reference requires explicit metric units")
        if self.semantics is not ElevationSemantics.TERRAIN_ELEVATION:
            raise ValueError("terrain reference must carry terrain-elevation meaning")
        if not isinstance(self.array, np.ndarray) or self.array.ndim != 2:
            raise ValueError("array must be an explicit 2D array")
        if self.array.dtype.kind != "f" or str(self.array.dtype) not in (
            "float32",
            "float64",
        ):
            raise ValueError("array must be float32/float64")
        if self.array.shape != (self.height, self.width):
            raise ValueError("array shape must match (height, width)")
        if self.dtype != str(self.array.dtype):
            raise ValueError("dtype label must match the array dtype")
        if (
            not isinstance(self.valid_mask, np.ndarray)
            or self.valid_mask.dtype.kind != "b"
            or self.valid_mask.shape != self.array.shape
        ):
            raise ValueError("valid_mask must be a bool array matching the grid shape")
        if self.invalid_count != int((~self.valid_mask).sum()):
            raise ValueError("invalid_count must equal the masked pixel count")
        if not math.isnan(self.nodata):
            raise ValueError("nodata must be the documented NaN marker")
        invalid_cells = self.array[~self.valid_mask]
        if invalid_cells.size and not bool(np.isnan(invalid_cells).all()):
            raise ValueError("masked pixels must carry the NaN nodata marker")
        valid_cells = self.array[self.valid_mask]
        if valid_cells.size and not bool(np.isfinite(valid_cells).all()):
            raise ValueError("valid pixels must all be finite")
        return self


class TerrainSample(BaseModel):
    """Typed terrain sampling outcome (invalid carries no values)."""

    model_config = ConfigDict(frozen=True)

    valid: bool
    elevation: float | None = Field(
        default=None, description="Terrain elevation when valid, else None."
    )
    row: int | None = Field(default=None, description="Integer row when resolved.")
    col: int | None = Field(default=None, description="Integer column when resolved.")
    pixel_row: float | None = Field(default=None, description="Continuous row (world sampling).")
    pixel_col: float | None = Field(default=None, description="Continuous column (world sampling).")
    x: float | None = Field(default=None, description="World X when placed.")
    y: float | None = Field(default=None, description="World Y when placed.")
    units: str = "meters"
    reference_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def _check_sample(self) -> TerrainSample:
        if self.valid and self.elevation is None:
            raise ValueError("valid samples must carry an elevation")
        if not self.valid and self.elevation is not None:
            raise ValueError("invalid samples must not invent elevations")
        if self.units != "meters":
            raise ValueError("terrain samples use explicit metric units")
        return self
