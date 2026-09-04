"""Target derivation, alignment, resolution recording, nodata."""

from pathlib import Path

import numpy as np
import pytest
import rasterio

from depthwizard.dem.build import build_terrain_reference
from depthwizard.dem.inspect import inspect_dem
from depthwizard.dem.target import target_grid_from_inspection
from depthwizard.errors import DemMismatchError, InvalidInputError, MissingCRSError
from depthwizard.geospatial.grids import TargetGrid
from depthwizard.geospatial.warp import ResamplingMethod
from depthwizard.ingestion.api import inspect_input
from tests.dem.support import dem_inspection, image_target, make_dem
from tests.ingestion.fixtures import make_geotiff


def test_target_from_georeferenced(tmp_path: Path) -> None:
    inspection = inspect_input(make_geotiff(tmp_path / "scene.tif"))
    target = target_grid_from_inspection(inspection)
    assert isinstance(target, TargetGrid)
    assert target.crs == "EPSG:32643"
    assert (target.width, target.height) == (5, 4)
    assert target.transform.as_tuple() == (100.0, 0.5, 0.0, 200.0, 0.0, -0.5)
    assert target.dtype == "float32"
    assert target.resolution == 0.5


def test_target_rejects_nongeoreferenced(tmp_path: Path) -> None:
    from tests.ingestion.fixtures import make_png as _png

    inspection = inspect_input(_png(tmp_path / "a.png"))
    with pytest.raises(MissingCRSError, match="non-georeferenced"):
        target_grid_from_inspection(inspection)


def test_target_rejects_wrong_type() -> None:
    with pytest.raises(TypeError, match="InputInspection"):
        target_grid_from_inspection("not-an-inspection")  # type: ignore[arg-type]


def test_native_alignment_fast_path(tmp_path: Path) -> None:
    inspection = dem_inspection(tmp_path)
    native = TargetGrid(
        crs=inspection.crs,
        transform=inspection.transform,
        width=inspection.width,
        height=inspection.height,
        dtype="float32",
        nodata=float("nan"),
        resolution=inspection.resolution,
    )
    grid = build_terrain_reference(inspection, native)
    assert (grid.width, grid.height) == (6, 5)
    assert grid.resampling is None
    assert grid.source_resolution == 1.0
    assert grid.target_resolution == 1.0
    assert grid.crs == "EPSG:32643"
    assert grid.invalid_count == 1
    # Ramp value at (0, 2) is 100 + 2 = 102.
    assert grid.array[0, 2] == 102.0


def test_image_grid_alignment(tmp_path: Path) -> None:
    inspection = dem_inspection(tmp_path)
    target = image_target(tmp_path)
    grid = build_terrain_reference(inspection, target)
    assert (grid.width, grid.height) == (5, 4)
    assert grid.crs == "EPSG:32643"
    assert grid.transform == target.transform
    assert grid.source_resolution == 1.0
    assert grid.target_resolution == 0.5
    assert grid.resampling is ResamplingMethod.NEAREST
    # The fixture DEM nodata cell (1, 1) covers four 0.5 m cells.
    assert grid.invalid_count == 4
    assert grid.array[0, 2] == 108.0
    assert grid.semantics.value == "terrain_elevation"


def test_cross_crs_alignment(tmp_path: Path) -> None:
    from rasterio.crs import CRS
    from rasterio.warp import transform_bounds

    # DEM box covering the image footprint, expressed in EPSG:4326
    # (derived at runtime, not hard-coded).
    lon0, lat0, lon1, lat1 = transform_bounds(
        CRS.from_string("EPSG:32643"),
        CRS.from_string("EPSG:4326"),
        100.0,
        198.0,
        102.5,
        200.0,
    )
    pixel = 0.005
    width = max(2, int((lon1 - lon0) / pixel))
    height = max(2, int((lat1 - lat0) / pixel))
    make_dem(
        tmp_path / "wgs.tif",
        crs="EPSG:4326",
        transform=(lon0, pixel, 0.0, lat1, 0.0, -pixel),
        width=width,
        height=height,
        nodata=None,
    )
    inspection = inspect_dem(tmp_path / "wgs.tif", vertical_units="meters")
    assert inspection.crs == "EPSG:4326"
    target = image_target(tmp_path)
    grid = build_terrain_reference(inspection, target)
    assert grid.crs == "EPSG:32643"
    assert (grid.width, grid.height) == (5, 4)
    assert grid.transform == target.transform
    assert grid.source_crs == "EPSG:4326"
    assert grid.invalid_count < grid.width * grid.height


def test_no_overlap_rejected(tmp_path: Path) -> None:
    inspection = dem_inspection(tmp_path)
    far = TargetGrid(
        crs="EPSG:32643",
        transform=inspection.transform.model_copy(update={"a": 10000.0, "d": 20000.0}),
        width=5,
        height=4,
        dtype="float32",
        nodata=float("nan"),
    )
    with pytest.raises(DemMismatchError, match="does not overlap"):
        build_terrain_reference(inspection, far)


def test_all_invalid_source_rejected(tmp_path: Path) -> None:
    make_dem(tmp_path / "void.tif", nodata=None)
    with rasterio.open(tmp_path / "void.tif", "r+") as dataset:
        dataset.write(np.full((5, 6), np.nan, dtype=np.float32), 1)
    inspection = inspect_dem(tmp_path / "void.tif", vertical_units="meters")
    with pytest.raises(InvalidInputError, match="no valid samples"):
        build_terrain_reference(inspection, image_target(tmp_path))


def test_bilinear_records_method(tmp_path: Path) -> None:
    inspection = dem_inspection(tmp_path)
    grid = build_terrain_reference(
        inspection, image_target(tmp_path), resampling=ResamplingMethod.BILINEAR
    )
    assert grid.resampling is ResamplingMethod.BILINEAR
    assert grid.semantics.value == "terrain_elevation"
