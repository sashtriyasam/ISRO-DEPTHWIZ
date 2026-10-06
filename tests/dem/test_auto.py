"""Automatic Copernicus DEM: tile naming, mirror reads, caching, offline mode."""

from pathlib import Path

import numpy as np
import pytest

from depthwizard.dem import auto
from depthwizard.errors import DemMismatchError
from depthwizard.ingestion.api import inspect_input


def test_tile_names() -> None:
    assert auto.tile_name(28, 77) == "Copernicus_DSM_COG_10_N28_00_E077_00_DEM"
    assert auto.tile_name(-34, -59) == "Copernicus_DSM_COG_10_S34_00_W059_00_DEM"


def test_tiles_for_spanning_bounds() -> None:
    assert auto.tiles_for((76.9, 27.9, 77.1, 28.1)) == [(27, 76), (27, 77), (28, 76), (28, 77)]


def _mirror_tile(root: Path, lat: int, lon: int, value: float) -> None:
    import rasterio
    from rasterio.transform import from_origin

    name = auto.tile_name(lat, lon)
    (root / name).mkdir(parents=True)
    with rasterio.open(
        root / name / f"{name}.tif",
        "w",
        driver="GTiff",
        width=60,
        height=60,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_origin(lon, lat + 1, 1 / 60, 1 / 60),
    ) as dst:
        dst.write(np.full((1, 60, 60), value, dtype="float32"))


def _scene(tmp_path: Path) -> Path:
    import rasterio
    from rasterio.transform import from_origin

    path = tmp_path / "scene.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=10,
        height=10,
        count=3,
        dtype="uint8",
        crs="EPSG:4326",
        transform=from_origin(77.2, 28.6, 0.0005, 0.0005),
    ) as dst:
        dst.write(np.full((3, 10, 10), 120, dtype="uint8"))
    return path


def test_fetch_reads_mirror_and_caches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    mirror = tmp_path / "mirror"
    _mirror_tile(mirror, 28, 77, 215.0)
    monkeypatch.setenv(auto.BASE_URL_ENV, str(mirror))
    inspection = inspect_input(_scene(tmp_path))
    first = auto.fetch_reference_dem(inspection, cache_dir=tmp_path / "cache")
    assert not first.from_cache
    import rasterio

    with rasterio.open(first.path) as ds:
        assert float(np.nanmean(ds.read(1))) == pytest.approx(215.0)
    monkeypatch.setenv(auto.OFFLINE_ENV, "1")
    again = auto.fetch_reference_dem(inspection, cache_dir=tmp_path / "cache")
    assert again.from_cache and again.path == first.path


def test_offline_without_cache_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(auto.OFFLINE_ENV, "1")
    inspection = inspect_input(_scene(tmp_path))
    with pytest.raises(DemMismatchError, match="network access is disabled"):
        auto.fetch_reference_dem(inspection, cache_dir=tmp_path / "cache")


def test_missing_tiles_are_sea_level(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "empty_mirror").mkdir()
    monkeypatch.setenv(auto.BASE_URL_ENV, str(tmp_path / "empty_mirror"))
    inspection = inspect_input(_scene(tmp_path))
    result = auto.fetch_reference_dem(inspection, cache_dir=tmp_path / "cache")
    assert result.ocean_tiles
