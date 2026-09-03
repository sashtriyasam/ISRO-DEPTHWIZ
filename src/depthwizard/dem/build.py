"""DEM-to-target alignment producing owned terrain reference grids.

Flow: validate inspection → read band → derive validity → check S7
compatibility → overlap-gate → align/reproject → sanitize → build.
The output records source and target resolutions separately: an
interpolated surface on a fine grid is never presented as fine
ground truth. No calibration, no DSM/AGL derivation, no export.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.dem.models import DEMInspection, TerrainReferenceGrid
from depthwizard.errors import (
    DemMismatchError,
    GeospatialProcessingError,
    InvalidInputError,
)
from depthwizard.geospatial.grids import TargetGrid, check_grid_compatibility
from depthwizard.geospatial.overlap import calculate_overlap
from depthwizard.geospatial.transforms import raster_bounds
from depthwizard.geospatial.warp import ResamplingMethod, align_raster
from depthwizard.version import __version__


def build_terrain_reference(
    inspection: DEMInspection,
    target: TargetGrid,
    *,
    resampling: ResamplingMethod = ResamplingMethod.NEAREST,
) -> TerrainReferenceGrid:
    """Align a validated DEM inspection to an explicit target grid.

    Raises :class:`DemMismatchError` for non-overlapping or uncovered
    targets, :class:`InvalidInputError` for all-invalid DEM sources,
    and :class:`GeospatialProcessingError` for other spatial failures.
    """
    if not isinstance(inspection, DEMInspection):
        raise TypeError(
            f"build_terrain_reference requires a DEMInspection; got {type(inspection).__name__}"
        )
    if not isinstance(target, TargetGrid):
        raise TypeError(
            f"build_terrain_reference requires a TargetGrid; got {type(target).__name__}"
        )
    source_grid = TargetGrid(
        crs=inspection.crs,
        transform=inspection.transform,
        width=inspection.width,
        height=inspection.height,
        dtype=inspection.dtype,
        nodata=inspection.nodata if inspection.nodata is not None else float("nan"),
        resolution=inspection.resolution,
    )
    target_bounds = raster_bounds(target.transform, target.width, target.height)
    overlap = calculate_overlap(inspection.bounds, inspection.crs, target_bounds, target.crs)
    if not overlap.intersects:
        raise DemMismatchError(
            f"DEM {inspection.display_name} ({inspection.crs}, "
            f"bounds {inspection.bounds.min_x},{inspection.bounds.min_y},"
            f"{inspection.bounds.max_x},{inspection.bounds.max_y}) does not "
            f"overlap the target grid ({target.crs}); refusing alignment "
            "instead of cropping the mismatch away"
        )
    data, file_mask = _read_dem_band(inspection)
    if not bool(file_mask.any()):
        raise InvalidInputError(f"DEM {inspection.display_name} contains no valid samples")
    working = _to_working_float(data)
    aligned = align_raster(
        np.where(file_mask, working, np.nan),
        source_grid,
        target,
        resampling=resampling,
    )
    array = aligned.array
    valid = aligned.valid_mask
    invalid_count = int((~valid).sum())
    if invalid_count == target.width * target.height:
        raise DemMismatchError(
            f"DEM {inspection.display_name} leaves the entire target grid "
            f"({target.width}x{target.height}) uncovered; no valid terrain "
            "reference exists"
        )
    if invalid_count == target.width * target.height:
        raise DemMismatchError(
            f"DEM {inspection.display_name} covers none of the target grid "
            f"({target.width}x{target.height}); no valid terrain reference exists"
        )
    native = check_grid_compatibility(source_grid, target).compatible
    provenance = ProductProvenance(
        source_input_id=inspection.display_name,
        input_checksum=inspection.sha256,
        software_version=__version__,
        generated_at=None,
        units="meters",
        semantic_meaning=ElevationSemantics.TERRAIN_ELEVATION.value,
    )
    return TerrainReferenceGrid(
        array=np.ascontiguousarray(array),
        valid_mask=np.ascontiguousarray(valid),
        width=target.width,
        height=target.height,
        dtype=str(array.dtype),
        units="meters",
        semantics=ElevationSemantics.TERRAIN_ELEVATION,
        nodata=float("nan"),
        invalid_count=invalid_count,
        crs=target.crs,
        transform=target.transform,
        bounds=target_bounds,
        resolution=target.resolution,
        source_dem_id=inspection.display_name,
        source_checksum=inspection.sha256,
        source_crs=inspection.crs,
        source_resolution=inspection.resolution,
        target_resolution=target.resolution,
        resampling=None if native else resampling,
        provenance=provenance,
    )


def _read_dem_band(inspection: DEMInspection) -> tuple[np.ndarray, np.ndarray]:
    """Read band 1 with its file validity mask (no mutation of source)."""
    import rasterio

    try:
        dataset = rasterio.open(Path(inspection.source_path))
    except Exception as exc:
        raise InvalidInputError(
            f"DEM source became unreadable: {inspection.display_name}: {exc}"
        ) from exc
    with dataset:
        try:
            data = dataset.read(1)
            mask = dataset.read_masks(1) != 0
        except Exception as exc:
            raise InvalidInputError(
                f"DEM band unreadable: {inspection.display_name}: {exc}"
            ) from exc
    finite = np.isfinite(data)
    if inspection.nodata is not None and np.isfinite(inspection.nodata):
        declared = data != inspection.nodata
        return data, mask & finite & declared
    return data, mask & finite


def _to_working_float(data: np.ndarray) -> np.ndarray:
    """Float working copy: preserve float dtypes, widen integers to float32."""
    if data.dtype.kind == "f":
        return data.astype(data.dtype, copy=True)
    if data.dtype.kind in "ui":
        return data.astype(np.float32)
    raise GeospatialProcessingError(
        f"DEM band dtype '{data.dtype}' is not a numeric elevation type"
    )
