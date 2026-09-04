"""Tiny deterministic DEM fixtures (programmatic, offline, tmp_path only).

Default DEM: 6x5 float32, EPSG:32643, 1 m pixels at (99, 201),
nodata -9999, ramp values 100+ with a valid 0.0 cell and one nodata
cell. Never committed, never downloaded.
"""

from pathlib import Path
from typing import Any

import numpy as np

from depthwizard.dem.inspect import inspect_dem
from depthwizard.dem.models import DEMInspection, TerrainReferenceGrid
from depthwizard.dem.target import target_grid_from_inspection
from depthwizard.geospatial.grids import TargetGrid
from depthwizard.ingestion.api import inspect_input
from tests.ingestion.fixtures import make_geotiff

DEM_CRS = "EPSG:32643"
DEM_TRANSFORM = (99.0, 1.0, 0.0, 201.0, 0.0, -1.0)


def make_dem(path: Path, **overrides: Any) -> Path:
    """Write a deterministic DEM GeoTIFF (kwargs override profile parts)."""
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import Affine

    width = overrides.get("width", 6)
    height = overrides.get("height", 5)
    count = overrides.get("count", 1)
    dtype = overrides.get("dtype", "float32")
    nodata = overrides.get("nodata", -9999.0)
    values = np.arange(width * height, dtype=np.float64).reshape(height, width)
    values = 100.0 + values
    values[0, 0] = 0.0
    marker = nodata if (nodata is not None and nodata == nodata) else float("nan")
    values[1, 1] = marker
    grid = np.stack([values] * count, axis=0).astype(dtype, copy=False)
    profile: dict[str, Any] = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": count,
        "dtype": dtype,
    }
    if "crs" not in overrides or overrides["crs"] is not None:
        profile["crs"] = CRS.from_string(overrides.get("crs", DEM_CRS))
    if "transform" not in overrides or overrides["transform"] is not None:
        raw = overrides.get("transform", DEM_TRANSFORM)
        profile["transform"] = Affine(raw[1], raw[2], raw[0], raw[4], raw[5], raw[3])
    if "nodata" not in overrides or overrides["nodata"] is not None:
        profile["nodata"] = nodata
    with rasterio.open(path, "w", **profile) as dataset:
        dataset.write(grid)
    return path


def dem_inspection(tmp_path: Path, name: str = "dem.tif", **overrides: Any) -> DEMInspection:
    """Inspect a freshly written DEM fixture (metric units declared)."""
    units = overrides.pop("vertical_units", "meters")
    return inspect_dem(make_dem(tmp_path / name, **overrides), vertical_units=units)


def image_target(tmp_path: Path) -> TargetGrid:
    """Target grid derived from the deterministic georeferenced fixture."""
    inspection = inspect_input(make_geotiff(tmp_path / "scene.tif"))
    return target_grid_from_inspection(inspection)


def native_grid(tmp_path: Path) -> TerrainReferenceGrid:
    """Terrain reference on the DEM's own grid (exact value preservation)."""
    from depthwizard.dem.build import build_terrain_reference

    inspection = dem_inspection(tmp_path)
    target = TargetGrid(
        crs=inspection.crs,
        transform=inspection.transform,
        width=inspection.width,
        height=inspection.height,
        dtype="float32",
        nodata=float("nan"),
        resolution=inspection.resolution,
    )
    return build_terrain_reference(inspection, target)
