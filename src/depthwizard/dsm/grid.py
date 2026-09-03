"""In-memory one-band DSM raster representation (meaning preserved).

``DSMGrid`` stores calibrated metric values as an explicit 2D float
array plus a dedicated validity mask, reusing the source product's
units, semantics, spatial context and provenance without
reinterpretation. ``DSMProfile`` prepares future-writer metadata only
— nothing here writes files.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.contracts.artifacts import METRIC_UNIT
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import ElevationSemantics, GeoreferencingLevel
from depthwizard.contracts.spatial import SpatialContext, SpatialKind

#: Documented nodata marker: NaN. A valid 0.0 stays valid; only
#: non-finite sources become nodata. NaN is the marker, never a value.
NODATA: float = float("nan")

#: Recorded future-writer driver. No writing happens in this milestone.
DRIVER = "GTiff"

#: DSM rasters are single-band: band 1 holds the scientific values.
BAND_COUNT = 1

_METRIC_SEMANTICS = frozenset(
    {
        ElevationSemantics.HEIGHT_AGL_NDSM,
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    }
)


class ResamplingPolicy(str, Enum):
    """Rasterization policies actually supported (no fake resampling)."""

    NO_RESAMPLING = "no_resampling"


class RasterizeOptions(BaseModel):
    """Small explicit rasterization configuration (1:1 defaults)."""

    model_config = ConfigDict(frozen=True)

    dtype: Literal["float32", "float64"] = Field(
        default="float32",
        description="Target storage dtype. float32 is the standard DSM "
        "interchange default; float64 preserves full source precision.",
    )
    resampling: ResamplingPolicy = Field(
        default=ResamplingPolicy.NO_RESAMPLING,
        description="Always 1:1 grid preservation this milestone.",
    )


class DSMGrid(BaseModel):
    """Owned 2D raster of calibrated metric values with validity mask.

    Controlled immutability: the model is frozen (no attribute
    reassignment) and factories always hand out freshly allocated
    arrays. Consumers must treat ``array``/``valid_mask`` as read-only
    (copy before mutating).
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    array: np.ndarray = Field(description="2D float array, shape (height, width).")
    valid_mask: np.ndarray = Field(
        description="2D bool array, True marks scientifically valid pixels."
    )
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    dtype: str = Field(description="Storage dtype name ('float32'/'float64').")
    units: str = Field(description="Always explicit metric units ('meters').")
    semantics: ElevationSemantics = Field(description="Preserved product meaning.")
    nodata: float = Field(description="Documented nodata marker (NaN).")
    invalid_count: int = Field(ge=0, description="Pixels masked as nodata.")
    resampling: ResamplingPolicy = ResamplingPolicy.NO_RESAMPLING
    georeferencing: GeoreferencingLevel = Field(description="Preserved, never upgraded.")
    spatial: SpatialContext = Field(description="Preserved source spatial context.")
    depth_model_name: str = Field(min_length=1)
    depth_model_version: str | None = None
    depth_checkpoint_id: str | None = None
    source_input_id: str | None = None
    source_checksum: str | None = None
    calibration_method: str = Field(min_length=1)
    calibration_reference: str = Field(min_length=1)
    calibration_scale: float
    calibration_offset: float
    calibration_valid_samples: int = Field(ge=0)
    provenance: ProductProvenance = Field(description="Reused product provenance.")

    @model_validator(mode="after")
    def _check_grid_honesty(self) -> DSMGrid:
        if self.units != METRIC_UNIT:
            raise ValueError(f"DSM grid requires metric units ('{METRIC_UNIT}')")
        if self.semantics not in _METRIC_SEMANTICS:
            raise ValueError("DSM grid requires a metric product meaning")
        if not isinstance(self.array, np.ndarray) or self.array.ndim != 2:
            raise ValueError("DSM array must be an explicit 2D array")
        if self.array.dtype.kind != "f" or str(self.array.dtype) not in (
            "float32",
            "float64",
        ):
            raise ValueError("DSM array must be float32/float64")
        if self.array.shape != (self.height, self.width):
            raise ValueError(
                f"array shape {self.array.shape} != (height, width) ({self.height}, {self.width})"
            )
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
        if self.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED:
            if self.spatial.kind is SpatialKind.PRESENT:
                raise ValueError("NON_GEOREFERENCED grid must not carry PRESENT details")
        return self

    def export_profile(self) -> DSMProfile:
        """Prepare future-writer metadata (no file I/O, values never invented)."""
        details = self.spatial.details if self.spatial.kind is SpatialKind.PRESENT else None
        return DSMProfile(
            driver=DRIVER,
            dtype=self.dtype,
            count=BAND_COUNT,
            width=self.width,
            height=self.height,
            crs=details.crs if details is not None else None,
            transform=details.transform.as_tuple()
            if details is not None and details.transform is not None
            else None,
            nodata=self.nodata,
        )


class DSMProfile(BaseModel):
    """Typed future-GeoTIFF-writer metadata (preparation only, no I/O)."""

    model_config = ConfigDict(frozen=True)

    driver: str = Field(min_length=1)
    dtype: str
    count: int = Field(description="Always 1: band 1 holds the science values.")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    crs: str | None = Field(default=None, description="CRS id, only when known.")
    transform: tuple[float, ...] | None = Field(
        default=None, description="6-tuple GDAL-order affine, only when known."
    )
    nodata: float = Field(description="Nodata marker mirrored from the grid.")
    tiled: bool = Field(
        default=False,
        description="Current grids are single in-memory arrays, never tiled.",
    )

    @model_validator(mode="after")
    def _check_profile_honesty(self) -> DSMProfile:
        if self.count != BAND_COUNT:
            raise ValueError("DSM profile is single-band (count must be 1)")
        if self.transform is not None and len(self.transform) != 6:
            raise ValueError("transform must be a 6-tuple GDAL-order affine")
        if self.transform is not None and self.crs is None:
            raise ValueError("a transform without CRS would be an orphan; refused")
        return self

    def to_rasterio_kwargs(self) -> dict[str, Any]:
        """Plain-data writer kwargs for the future exporter.

        The 6-tuple transform is left in GDAL order; the exporter
        converts it to the writer's affine type. No file is opened here.
        """
        return {
            "driver": self.driver,
            "dtype": self.dtype,
            "count": self.count,
            "width": self.width,
            "height": self.height,
            "crs": self.crs,
            "transform": self.transform,
            "nodata": self.nodata,
        }
