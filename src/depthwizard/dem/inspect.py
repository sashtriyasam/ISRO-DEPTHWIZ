"""Local DEM source inspection (metadata only, offline, GeoTIFF-first).

Reads raster profile metadata without loading pixel arrays. Vertical
units have no trustworthy in-file encoding in this stack, so metric
use always requires an explicit caller declaration (meters only).
"""

from __future__ import annotations

import warnings
from pathlib import Path

from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.dem.models import DEMInspection
from depthwizard.errors import (
    GeospatialProcessingError,
    InvalidInputError,
    MissingCRSError,
    UnsupportedFormatError,
)
from depthwizard.geospatial.transforms import from_affine, raster_bounds, require_invertible
from depthwizard.ingestion.checksum import sha256_file
from depthwizard.ingestion.formats import DetectedFormat
from depthwizard.ingestion.models import InspectionStatus

_TIFF_SUFFIXES = frozenset({".tif", ".tiff"})


def inspect_dem(path: str | Path, *, vertical_units: str | None = None) -> DEMInspection:
    """Inspect a local DEM raster and return its typed description.

    Raises :class:`InvalidInputError` for missing/unreadable/corrupt
    or structurally unsuitable files, :class:`UnsupportedFormatError`
    outside GeoTIFF, :class:`MissingCRSError` without CRS, and
    :class:`GeospatialProcessingError` for missing/singular
    transforms, bad resolution, or non-metre vertical units.
    """
    candidate = Path(path)
    display = candidate.name or str(candidate)
    try:
        is_file = candidate.is_file()
    except OSError as exc:
        raise InvalidInputError(f"unreadable DEM path: {display}: {exc}") from exc
    if not is_file:
        if candidate.exists():
            raise InvalidInputError(f"DEM input is not a file (directory?): {display}")
        raise InvalidInputError(f"DEM file not found: {display}")
    try:
        size = candidate.stat().st_size
    except OSError as exc:
        raise InvalidInputError(f"unreadable DEM file: {display}: {exc}") from exc
    if size == 0:
        raise InvalidInputError(f"DEM file is empty (0 bytes): {display}")
    if candidate.suffix.lower() not in _TIFF_SUFFIXES:
        raise UnsupportedFormatError(
            f"unsupported DEM format: {display} (S8 supports local GeoTIFF DEM input: .tif, .tiff)"
        )
    if vertical_units != "meters":
        raise GeospatialProcessingError(
            f"DEM metric use requires explicit vertical_units='meters'; "
            f"got {vertical_units!r} for {display} (no trustworthy in-file "
            "encoding exists in this stack)"
        )

    import rasterio
    from rasterio.errors import NotGeoreferencedWarning
    from rasterio.transform import Affine

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            dataset = rasterio.open(candidate)
        except Exception as exc:
            raise InvalidInputError(f"unreadable DEM raster: {display}: {exc}") from exc
        try:
            with dataset:
                warned = any(issubclass(item.category, NotGeoreferencedWarning) for item in caught)
                transform = dataset.transform
                if dataset.count != 1:
                    raise InvalidInputError(
                        f"DEM must carry a single elevation band, got {dataset.count} in {display}"
                    )
                dtype = dataset.dtypes[0]
                import numpy as np

                if np.dtype(dtype).kind not in "uif":
                    raise InvalidInputError(
                        f"DEM band must be numeric (uint/int/float), got '{dtype}' in {display}"
                    )
                crs = dataset.crs
                if crs is None:
                    raise MissingCRSError(f"DEM terrain use requires a CRS, none in {display}")
                if warned or transform == Affine.identity():
                    raise GeospatialProcessingError(f"DEM has no geotransform: {display}")
                contract_transform = from_affine(transform)
                require_invertible(contract_transform)
                bounds = raster_bounds(contract_transform, dataset.width, dataset.height)
                res_x, res_y = dataset.res
                if res_x <= 0 or res_y <= 0:
                    raise GeospatialProcessingError(
                        f"DEM has non-positive resolution {dataset.res!r}: {display}"
                    )
                resolution = float(res_x) if res_x == res_y else None
                metadata = {
                    "reader": f"rasterio-{rasterio.__version__}",
                    "driver": str(dataset.driver),
                    "dtype": dtype,
                }
                return DEMInspection(
                    source_path=str(candidate),
                    display_name=display,
                    file_size=size,
                    sha256=sha256_file(candidate),
                    detected_format=DetectedFormat.TIFF,
                    width=int(dataset.width),
                    height=int(dataset.height),
                    band_count=1,
                    dtype=dtype,
                    nodata=None if dataset.nodata is None else float(dataset.nodata),
                    crs=crs.to_string(),
                    transform=contract_transform,
                    bounds=bounds,
                    resolution=resolution,
                    vertical_units="meters",
                    vertical_semantics=ElevationSemantics.TERRAIN_ELEVATION,
                    source_format_metadata=metadata,
                    status=InspectionStatus.VALID,
                )
        except (InvalidInputError, MissingCRSError, GeospatialProcessingError):
            raise
        except Exception as exc:
            raise InvalidInputError(f"unreadable DEM raster: {display}: {exc}") from exc
