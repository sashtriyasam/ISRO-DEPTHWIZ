"""Minimal raster reprojection and alignment (rasterio.warp-backed).

Caller-specified target grids only — no silent resolution changes.
Resampling is explicit per call (nearest default: conservative, never
invents values; bilinear available for continuous fields). Nodata and
masks follow the repository policy: finite stays valid (including
0.0), non-finite stays invalid, derived masks come from output
finiteness. Sources are never mutated; outputs are freshly owned.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.spatial import AffineTransform
from depthwizard.errors import GeospatialProcessingError
from depthwizard.geospatial.grids import TargetGrid
from depthwizard.geospatial.transforms import to_affine


class ResamplingMethod(str, Enum):
    """Resampling methods actually supported (caller-specified)."""

    NEAREST = "nearest"
    BILINEAR = "bilinear"


class ReprojectedRaster(BaseModel):
    """Owned reprojection/alignment output with validity mask."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    array: np.ndarray = Field(description="2D float array, shape (height, width).")
    valid_mask: np.ndarray = Field(description="2D bool array, True marks valid pixels.")
    grid: TargetGrid = Field(description="Target grid actually produced.")
    resampling: ResamplingMethod = Field(
        description="Method requested (bypassed without warp only for identical grids)."
    )
    source_crs: str = Field(description="Source CRS identifier.")
    provenance: ProductProvenance | None = Field(
        default=None, description="Source provenance passthrough, when provided."
    )

    @model_validator(mode="after")
    def _check_output(self) -> ReprojectedRaster:
        if not isinstance(self.array, np.ndarray) or self.array.ndim != 2:
            raise ValueError("array must be an explicit 2D array")
        if self.array.dtype.kind != "f":
            raise ValueError("array must be floating point")
        if self.array.shape != (self.grid.height, self.grid.width):
            raise ValueError("array shape must match the target grid")
        if (
            not isinstance(self.valid_mask, np.ndarray)
            or self.valid_mask.dtype.kind != "b"
            or self.valid_mask.shape != self.array.shape
        ):
            raise ValueError("valid_mask must be a bool array matching the array shape")
        invalid_cells = self.array[~self.valid_mask]
        if invalid_cells.size and not bool(np.isnan(invalid_cells).all()):
            raise ValueError("masked pixels must carry the NaN nodata marker")
        valid_cells = self.array[self.valid_mask]
        if valid_cells.size and not bool(np.isfinite(valid_cells).all()):
            raise ValueError("valid pixels must all be finite")
        return self


def _resampling_flag(method: ResamplingMethod) -> Any:
    """Map the contract enum to the rasterio resampling flag (Any: untyped lib)."""
    from rasterio.enums import Resampling

    return Resampling.nearest if method is ResamplingMethod.NEAREST else Resampling.bilinear


def reproject_array(
    source: np.ndarray,
    source_crs: str,
    source_transform: AffineTransform,
    target: TargetGrid,
    source_nodata: float = float("nan"),
    resampling: ResamplingMethod = ResamplingMethod.NEAREST,
    provenance: ProductProvenance | None = None,
) -> ReprojectedRaster:
    """Reproject a 2D float array onto an explicit target grid.

    Returns freshly owned output; the source is never mutated. Output
    dtype matches the source dtype (no silent downcasting). The valid
    mask derives from output finiteness; NaN initializes all
    uncovered pixels.
    """
    from rasterio.crs import CRS
    from rasterio.warp import reproject

    if not isinstance(source, np.ndarray) or source.ndim != 2:
        raise GeospatialProcessingError("reprojection source must be a 2D array")
    if source.dtype.kind != "f":
        raise GeospatialProcessingError("reprojection source must be floating point")
    try:
        src_crs = CRS.from_string(source_crs)
        dst_crs = CRS.from_string(target.crs)
    except Exception as exc:
        raise GeospatialProcessingError(f"invalid CRS for reprojection: {exc}") from exc
    height, width = target.height, target.width
    destination = np.full((height, width), float("nan"), dtype=source.dtype)
    try:
        reproject(
            source,
            destination,
            src_transform=to_affine(source_transform),
            src_crs=src_crs,
            src_nodata=source_nodata,
            dst_transform=to_affine(target.transform),
            dst_crs=dst_crs,
            dst_nodata=float("nan"),
            resampling=_resampling_flag(resampling),
        )
    except Exception as exc:
        raise GeospatialProcessingError(f"raster reprojection failed: {exc}") from exc
    valid = np.isfinite(destination)
    result = destination.copy()
    result[~valid] = float("nan")
    return ReprojectedRaster(
        array=result,
        valid_mask=np.ascontiguousarray(valid),
        grid=target,
        resampling=resampling,
        source_crs=source_crs,
        provenance=provenance,
    )


def align_raster(
    source: np.ndarray,
    source_grid: TargetGrid,
    target_grid: TargetGrid,
    resampling: ResamplingMethod = ResamplingMethod.NEAREST,
    provenance: ProductProvenance | None = None,
) -> ReprojectedRaster:
    """Align a raster to a target grid (copy fast-path when identical).

    Identical grids (same CRS/transform/dims) return an owned copy with
    no warp — resampling is recorded as requested but not applied, and
    documented as such. Anything else goes through ``reproject_array``.
    """
    from depthwizard.geospatial.grids import check_grid_compatibility

    if not isinstance(source, np.ndarray) or source.ndim != 2:
        raise GeospatialProcessingError("alignment source must be a 2D array")
    if source.shape != (source_grid.height, source_grid.width):
        raise GeospatialProcessingError(
            f"source array shape {source.shape} != source grid "
            f"({source_grid.height}, {source_grid.width})"
        )
    if check_grid_compatibility(source_grid, target_grid).compatible:
        owned = source.copy()
        if owned.dtype.kind != "f":
            raise GeospatialProcessingError("alignment source must be floating point")
        valid = np.isfinite(owned)
        cleaned = owned.copy()
        cleaned[~valid] = float("nan")
        return ReprojectedRaster(
            array=cleaned,
            valid_mask=np.ascontiguousarray(valid),
            grid=target_grid,
            resampling=resampling,
            source_crs=source_grid.crs,
            provenance=provenance,
        )
    return reproject_array(
        source,
        source_grid.crs,
        source_grid.transform,
        target_grid,
        source_nodata=float("nan"),
        resampling=resampling,
        provenance=provenance,
    )
