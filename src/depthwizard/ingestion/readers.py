"""Format readers: Pillow for PNG/JPEG, rasterio for TIFF/GeoTIFF.

Readers decode just enough to validate the file and capture metadata.
Pixel arrays are never returned or stored. Lower-level exceptions are
wrapped into DepthWizard domain errors (originals chained as context).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from depthwizard.contracts.semantics import GeoreferencingLevel
from depthwizard.contracts.spatial import (
    AffineTransform,
    Bounds,
    SpatialContext,
    SpatialDetails,
    SpatialKind,
)
from depthwizard.errors import InvalidInputError
from depthwizard.ingestion.formats import DetectedFormat

if TYPE_CHECKING:
    from rasterio.transform import Affine

_PILLOW_FORMATS: dict[DetectedFormat, str] = {
    DetectedFormat.PNG: "PNG",
    DetectedFormat.JPEG: "JPEG",
}


@dataclass(frozen=True)
class RasterFacts:
    """Validated metadata captured by a reader (no pixel data)."""

    detected_format: DetectedFormat
    width: int
    height: int
    band_count: int | None
    dtype: str | None
    georeferencing: GeoreferencingLevel
    spatial: SpatialContext
    source_format_metadata: dict[str, str]


def inspect_pillow(path: Path, display: str, claimed: DetectedFormat) -> RasterFacts:
    """Validate a PNG/JPEG with Pillow and capture its metadata.

    Classifies as NON_GEOREFERENCED. EXIF/GPS, filenames and textual
    metadata are deliberately ignored: no geospatial semantics are
    inferred for plain images.
    """
    from PIL import Image

    expected = _PILLOW_FORMATS[claimed]
    try:
        with Image.open(path) as img:
            img.load()  # force decode: proves the file is a readable image
            decoded_format = img.format
            width, height = img.size
            mode = img.mode
            bands = Image.getmodebands(mode)
    except Exception as exc:
        raise InvalidInputError(f"unreadable {claimed.value} image: {display}: {exc}") from exc
    if decoded_format != expected:
        raise InvalidInputError(
            f"mislabeled input: {display} claims {claimed.value} "
            f"but decodes as {decoded_format or 'unknown'}"
        )
    from PIL import __version__ as pillow_version

    return RasterFacts(
        detected_format=claimed,
        width=width,
        height=height,
        band_count=bands,
        dtype=mode,
        georeferencing=GeoreferencingLevel.NON_GEOREFERENCED,
        spatial=SpatialContext(kind=SpatialKind.NOT_APPLICABLE),
        source_format_metadata={
            "reader": f"pillow-{pillow_version}",
            "mode": mode,
            "decoded_format": decoded_format or "unknown",
        },
    )


def _affine_from_rasterio(transform: Affine) -> AffineTransform:
    """Map a rasterio Affine to the foundation contract (GDAL tag order).

    Delegates to the shared geospatial converter (single mapping).
    """
    from depthwizard.geospatial.transforms import from_affine

    return from_affine(transform)


def inspect_geotiff(path: Path, display: str) -> RasterFacts:
    """Validate a TIFF/GeoTIFF with rasterio and capture its metadata.

    A readable raster *with* a CRS classifies as
    GEOREFERENCED_NO_ELEVATION_REFERENCE (never DEM/GCP-supported here).
    Without a CRS it is NON_GEOREFERENCED: the identity fallback
    transform is not treated as georeferencing. No reprojection,
    resampling, alignment or elevation work is performed.
    """
    import rasterio
    from rasterio.errors import NotGeoreferencedWarning

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        try:
            dataset = rasterio.open(path)
        except Exception as exc:
            raise InvalidInputError(f"unreadable tiff raster: {display}: {exc}") from exc
        try:
            with dataset:
                if dataset.driver != "GTiff":
                    raise InvalidInputError(
                        f"mislabeled input: {display} claims tiff but driver is {dataset.driver}"
                    )
                width = int(dataset.width)
                height = int(dataset.height)
                band_count = int(dataset.count)
                dtypes = tuple(dataset.dtypes)
                dtype: str | None = dtypes[0] if len(set(dtypes)) == 1 else None
                try:
                    crs = dataset.crs
                    crs_id = None if crs is None else crs.to_string()
                except Exception as exc:
                    raise InvalidInputError(f"unreadable CRS metadata: {display}: {exc}") from exc
                metadata: dict[str, str] = {
                    "reader": f"rasterio-{rasterio.__version__}",
                    "driver": str(dataset.driver),
                }
                if dtype is None:
                    metadata["dtypes"] = ",".join(dtypes)
                if crs_id is None:
                    return RasterFacts(
                        detected_format=DetectedFormat.TIFF,
                        width=width,
                        height=height,
                        band_count=band_count,
                        dtype=dtype,
                        georeferencing=GeoreferencingLevel.NON_GEOREFERENCED,
                        spatial=SpatialContext(kind=SpatialKind.UNAVAILABLE),
                        source_format_metadata={**metadata, "source": "tiff-header"},
                    )
                res_x, res_y = dataset.res
                resolution = float(res_x) if res_x == res_y else None
                if resolution is None:
                    metadata["res_x"] = str(res_x)
                    metadata["res_y"] = str(res_y)
                bounds = dataset.bounds
                nodata = dataset.nodata
                details = SpatialDetails(
                    crs=crs_id,
                    transform=_affine_from_rasterio(dataset.transform),
                    bounds=Bounds(
                        min_x=float(bounds.left),
                        min_y=float(bounds.bottom),
                        max_x=float(bounds.right),
                        max_y=float(bounds.top),
                    ),
                    resolution_gsd=resolution,
                    nodata=None if nodata is None else float(nodata),
                    raster_width=width,
                    raster_height=height,
                    source="geotiff-header",
                )
                return RasterFacts(
                    detected_format=DetectedFormat.TIFF,
                    width=width,
                    height=height,
                    band_count=band_count,
                    dtype=dtype,
                    georeferencing=GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE,
                    spatial=SpatialContext(kind=SpatialKind.PRESENT, details=details),
                    source_format_metadata=metadata,
                )
        except InvalidInputError:
            raise
        except Exception as exc:
            raise InvalidInputError(f"unreadable tiff raster: {display}: {exc}") from exc
