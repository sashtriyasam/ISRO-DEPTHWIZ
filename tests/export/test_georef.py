"""Georeferencing round-trip: CRS/transform/bounds/resolution fidelity."""

from pathlib import Path

from depthwizard.contracts.semantics import GeoreferencingLevel
from depthwizard.export import export_geotiff
from tests.export.support import absolute_grid, agl_grid, read_all


def test_georeferenced_round_trip(tmp_path: Path) -> None:
    grid = absolute_grid(tmp_path)
    target = tmp_path / "geo.tif"
    result = export_geotiff(grid, target)
    assert result.crs == "EPSG:32643"
    assert result.transform == (100.0, 0.5, 0.0, 200.0, 0.0, -0.5)
    data, _, profile = read_all(target)
    assert tuple(data.shape) == (4, 5)
    assert bool((data == grid.array).all())


def test_crs_structured_equality(tmp_path: Path) -> None:
    import rasterio
    from rasterio.crs import CRS

    grid = absolute_grid(tmp_path)
    target = tmp_path / "geo.tif"
    export_geotiff(grid, target)
    with rasterio.open(target) as dataset:
        assert dataset.crs is not None
        assert dataset.crs == CRS.from_epsg(32643)
        assert dataset.crs.to_string() == "EPSG:32643"
        assert tuple(dataset.bounds) == (100.0, 198.0, 102.5, 200.0)
        assert tuple(dataset.res) == (0.5, 0.5)


def test_nongeoreferenced_honest(tmp_path: Path) -> None:
    import warnings

    import rasterio
    from rasterio.errors import NotGeoreferencedWarning

    grid = agl_grid(tmp_path)
    target = tmp_path / "plain.tif"
    result = export_geotiff(grid, target)
    assert result.crs is None
    assert result.transform is None
    assert grid.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.open(target) as dataset:
            assert dataset.crs is None
    data, _, _ = read_all(target)
    assert tuple(data.shape) == (6, 8)
