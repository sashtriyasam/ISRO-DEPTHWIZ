"""Automatic reference DEM for georeferenced inputs (Copernicus GLO-30).

Final evaluation supplies only GeoTIFF imagery and scores the absolute DSM
against SRTM/Copernicus-class DEMs, so the app must source its own
reference. This module reads the Copernicus DEM GLO-30 cloud-optimised
GeoTIFFs (open data on AWS, no key) for exactly the image footprint plus a
margin, mosaics the 1°x1° tiles and caches the result as a local GeoTIFF
that the existing DEM alignment/calibration path consumes.

* Only the needed window of each tile is read (HTTP range requests).
* Results are cached under ``<data-dir>/dem-cache`` keyed by footprint, so
  repeated runs and offline reuse need no network.
* ``DW_DEM_OFFLINE=1`` forbids network access (cache only);
  ``DW_DEM_BASE_URL`` points at a mirror with the same layout.
* Tiles absent from the dataset are open ocean: they are filled with 0 m
  (sea level) and reported, never silently invented over land.
"""

from __future__ import annotations

import hashlib
import math
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from depthwizard.errors import DemMismatchError, GeospatialProcessingError
from depthwizard.ingestion.models import InputInspection

#: Copernicus DEM GLO-30 public bucket (1 arc-second, EGM2008 heights).
DEFAULT_BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com"
BASE_URL_ENV = "DW_DEM_BASE_URL"
OFFLINE_ENV = "DW_DEM_OFFLINE"

#: Source identity recorded in calibration provenance.
SOURCE_ID = "copernicus-dem-glo30"

#: 1 arc-second grid of GLO-30 (below 50° latitude).
ARCSEC = 1.0 / 3600.0

#: Extra DEM pixels around the footprint so bilinear sampling has support.
MARGIN_PIXELS = 3


@dataclass(frozen=True)
class AutoDem:
    """A cached reference DEM covering an input footprint."""

    path: Path
    source: str
    tiles: tuple[str, ...]
    ocean_tiles: tuple[str, ...] = field(default_factory=tuple)
    from_cache: bool = False


def tile_name(lat_floor: int, lon_floor: int) -> str:
    """Copernicus tile identifier for the 1°x1° cell at (lat, lon) floors."""
    ns = "N" if lat_floor >= 0 else "S"
    ew = "E" if lon_floor >= 0 else "W"
    return f"Copernicus_DSM_COG_10_{ns}{abs(lat_floor):02d}_00_{ew}{abs(lon_floor):03d}_00_DEM"


def tile_url(name: str, base_url: str | None = None) -> str:
    """HTTPS URL of a GLO-30 tile."""
    base = (base_url or os.environ.get(BASE_URL_ENV) or DEFAULT_BASE_URL).rstrip("/")
    return f"{base}/{name}/{name}.tif"


def footprint_lonlat(inspection: InputInspection) -> tuple[float, float, float, float]:
    """Image footprint in EPSG:4326 (west, south, east, north)."""
    from rasterio.warp import transform_bounds

    details = inspection.spatial.details
    if details is None or details.crs is None or details.bounds is None:
        raise DemMismatchError("automatic DEM needs a georeferenced input with CRS and bounds")
    b = details.bounds
    west, south, east, north = transform_bounds(
        details.crs, "EPSG:4326", b.min_x, b.min_y, b.max_x, b.max_y, densify_pts=21
    )
    return float(west), float(south), float(east), float(north)


def tiles_for(bounds: tuple[float, float, float, float]) -> list[tuple[int, int]]:
    """(lat_floor, lon_floor) of every 1° tile intersecting the bounds."""
    west, south, east, north = bounds
    lats = range(math.floor(south), math.floor(north - 1e-12) + 1)
    lons = range(math.floor(west), math.floor(east - 1e-12) + 1)
    return [(lat, lon) for lat in lats for lon in lons]


def _cache_dir() -> Path:
    from depthwizard.runtime.diagnostics import default_data_dir

    return default_data_dir() / "dem-cache"


def _cache_key(bounds: tuple[float, float, float, float]) -> str:
    text = ",".join(f"{v:.6f}" for v in bounds)
    return hashlib.sha256(f"{SOURCE_ID}|{text}".encode()).hexdigest()[:24]


def fetch_reference_dem(
    inspection: InputInspection,
    cache_dir: Path | None = None,
    base_url: str | None = None,
) -> AutoDem:
    """Return a local GeoTIFF of Copernicus GLO-30 covering the input footprint."""
    west, south, east, north = footprint_lonlat(inspection)
    pad = MARGIN_PIXELS * ARCSEC
    bounds = (west - pad, south - pad, east + pad, north + pad)
    folder = cache_dir or _cache_dir()
    target = folder / f"{_cache_key(bounds)}.tif"
    names = tuple(tile_name(lat, lon) for lat, lon in tiles_for(bounds))
    if target.is_file():
        return AutoDem(path=target, source=SOURCE_ID, tiles=names, from_cache=True)
    if os.environ.get(OFFLINE_ENV) == "1":
        raise DemMismatchError(
            "no cached reference DEM for this footprint and network access is disabled "
            f"({OFFLINE_ENV}=1); attach a DEM GeoTIFF or GCP CSV instead"
        )
    folder.mkdir(parents=True, exist_ok=True)
    array, transform, ocean = _read_mosaic(bounds, names, base_url)
    _write_geotiff(target, array, transform)
    return AutoDem(path=target, source=SOURCE_ID, tiles=names, ocean_tiles=tuple(ocean))


def _read_mosaic(
    bounds: tuple[float, float, float, float], names: tuple[str, ...], base_url: str | None
) -> tuple[np.ndarray, object, list[str]]:
    """Read the bounds from each tile window onto one 1-arcsec EPSG:4326 grid."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.transform import from_origin
    from rasterio.vrt import WarpedVRT

    west, south, east, north = bounds
    width = max(1, math.ceil((east - west) / ARCSEC))
    height = max(1, math.ceil((north - south) / ARCSEC))
    transform = from_origin(west, north, ARCSEC, ARCSEC)
    mosaic: np.ndarray = np.zeros((height, width), dtype=np.float32)
    covered: np.ndarray = np.zeros((height, width), dtype=bool)
    ocean: list[str] = []
    env = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
        "GDAL_HTTP_MAX_RETRY": "3",
        "GDAL_HTTP_RETRY_DELAY": "1",
    }
    with rasterio.Env(**env):
        for name in names:
            url = tile_url(name, base_url)
            try:
                dataset = rasterio.open(url)
            except Exception as exc:
                if _is_missing(exc):
                    ocean.append(name)  # GLO-30 omits all-water tiles
                    continue
                raise GeospatialProcessingError(
                    f"reference DEM tile unreachable ({name}): {exc}"
                ) from exc
            with (
                dataset,
                WarpedVRT(
                    dataset,
                    crs="EPSG:4326",
                    transform=transform,
                    width=width,
                    height=height,
                    resampling=Resampling.bilinear,
                    src_nodata=dataset.nodata,
                    nodata=float("nan"),
                ) as vrt,
            ):
                data = vrt.read(1).astype(np.float32)
            valid = np.isfinite(data)
            mosaic[valid] = data[valid]
            covered |= valid
    if not covered.any() and not ocean:
        raise DemMismatchError("reference DEM tiles did not cover the input footprint")
    # Pixels from absent (all-water) tiles stay at 0 m = sea level.
    return mosaic, transform, ocean


def _is_missing(exc: Exception) -> bool:
    text = str(exc).lower()
    return "404" in text or "does not exist" in text or "no such file" in text


def _write_geotiff(path: Path, array: np.ndarray, transform: object) -> None:
    import rasterio

    tmp = path.with_suffix(".tmp.tif")
    with rasterio.open(
        tmp,
        "w",
        driver="GTiff",
        width=array.shape[1],
        height=array.shape[0],
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=float("nan"),
        compress="deflate",
    ) as dst:
        dst.write(array, 1)
    os.replace(tmp, path)
