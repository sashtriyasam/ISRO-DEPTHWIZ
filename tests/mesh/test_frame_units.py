"""Mesh horizontal frame: metres only for projected metric CRSs."""

from pathlib import Path

import numpy as np
import pytest

from depthwizard.backends.synthetic import SyntheticDepthBackend
from depthwizard.calibration.selection import DevCalibrationProvider
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.dsm.rasterize import rasterize_height_product
from depthwizard.geospatial.crs import crs_is_projected_metric
from depthwizard.height.factory import create_scientific_height_product
from depthwizard.ingestion.api import inspect_input
from depthwizard.mesh.build import build_terrain_mesh
from depthwizard.mesh.models import CoordinateFrame


def _mesh_for_crs(tmp_path: Path, crs: str, pixel: float):  # type: ignore[no-untyped-def]
    import rasterio
    from rasterio.transform import Affine

    path = tmp_path / "scene.tif"
    data = np.arange(3 * 6 * 6, dtype=np.uint8).reshape(3, 6, 6)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=6,
        width=6,
        count=3,
        dtype="uint8",
        crs=crs,
        transform=Affine(pixel, 0.0, 73.0, 0.0, -pixel, 19.0),
    ) as dst:
        dst.write(data)
    inspection = inspect_input(path)
    depth = SyntheticDepthBackend().estimate_depth(inspection)
    target = ElevationSemantics.ABSOLUTE_ELEVATION_DSM
    calibration = DevCalibrationProvider(target).calibrate(depth)
    grid = rasterize_height_product(create_scientific_height_product(depth, calibration, target))
    return build_terrain_mesh(grid)


def test_geographic_crs_mesh_stays_in_pixel_frame(tmp_path: Path) -> None:
    mesh = _mesh_for_crs(tmp_path, "EPSG:4326", 1e-5)
    assert mesh.frame is CoordinateFrame.LOCAL
    xs = np.asarray(mesh.vertices)[:, 0]
    # Pixel indices, never 1e-5-degree offsets beside metre heights.
    assert float(xs.max() - xs.min()) == pytest.approx(5.0)


def test_projected_metric_crs_mesh_is_georeferenced(tmp_path: Path) -> None:
    mesh = _mesh_for_crs(tmp_path, "EPSG:32643", 0.5)
    assert mesh.frame is CoordinateFrame.GEOREFERENCED_LOCAL
    xs = np.asarray(mesh.vertices)[:, 0]
    assert float(xs.max() - xs.min()) == pytest.approx(2.5)


def test_crs_is_projected_metric() -> None:
    assert crs_is_projected_metric("EPSG:32643")
    assert not crs_is_projected_metric("EPSG:4326")
    assert not crs_is_projected_metric(None)
    assert not crs_is_projected_metric("not-a-crs")
