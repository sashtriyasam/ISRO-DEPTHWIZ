"""Georeferencing preservation and future-writer profile preparation."""

import math
from pathlib import Path

from depthwizard.contracts.semantics import GeoreferencingLevel
from depthwizard.contracts.spatial import SpatialKind
from depthwizard.dsm import DSMProfile, rasterize_height_product
from tests.dsm.support import absolute_geotiff_product, agl_png_product


def test_georeferenced_metadata_preserved(tmp_path: Path) -> None:
    product, _, _ = absolute_geotiff_product(tmp_path)
    grid = rasterize_height_product(product)
    assert grid.georeferencing is GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE
    assert grid.spatial.kind is SpatialKind.PRESENT
    assert grid.spatial == product.spatial
    details = grid.spatial.details
    assert details is not None
    assert details.crs == "EPSG:32643"
    assert details.resolution_gsd == 0.5


def test_nongeoreferenced_stays_absent(tmp_path: Path) -> None:
    product, _, _ = agl_png_product(tmp_path)
    grid = rasterize_height_product(product)
    assert grid.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED
    assert grid.spatial.kind is SpatialKind.NOT_APPLICABLE
    profile = grid.export_profile()
    assert profile.crs is None
    assert profile.transform is None


def test_profile_georeferenced(tmp_path: Path) -> None:
    product, _, _ = absolute_geotiff_product(tmp_path)
    grid = rasterize_height_product(product)
    profile = grid.export_profile()
    assert isinstance(profile, DSMProfile)
    assert profile.driver == "GTiff"
    assert profile.dtype == "float32"
    assert profile.count == 1
    assert (profile.width, profile.height) == (5, 4)
    assert profile.crs == "EPSG:32643"
    assert profile.transform == (100.0, 0.5, 0.0, 200.0, 0.0, -0.5)
    assert math.isnan(profile.nodata)
    assert profile.tiled is False


def test_profile_kwargs_shape(tmp_path: Path) -> None:
    product, _, _ = absolute_geotiff_product(tmp_path)
    kwargs = rasterize_height_product(product).export_profile().to_rasterio_kwargs()
    assert kwargs == {
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "width": 5,
        "height": 4,
        "crs": "EPSG:32643",
        "transform": (100.0, 0.5, 0.0, 200.0, 0.0, -0.5),
        "nodata": kwargs["nodata"],
    }
    assert math.isnan(kwargs["nodata"])
