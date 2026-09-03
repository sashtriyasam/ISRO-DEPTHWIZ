"""Basic export: file creation, read-back data/metadata, absolute variant."""

import math
from pathlib import Path

import numpy as np
import pytest

from depthwizard.dsm import DSMGrid
from depthwizard.errors import ExportError
from depthwizard.export import ExportResult, export_geotiff
from tests.export.support import absolute_grid, agl_grid, read_all


def test_basic_agl_export(tmp_path: Path) -> None:
    grid = agl_grid(tmp_path)
    target = tmp_path / "dsm.tif"
    result = export_geotiff(grid, target)
    assert isinstance(result, ExportResult)
    assert result.verified is True
    assert target.exists()
    assert (result.width, result.height) == (8, 6)
    assert result.dtype == "float32"
    assert result.compression == "deflate"
    assert math.isnan(result.nodata)
    assert result.crs is None
    assert result.transform is None
    data, mask, profile = read_all(target)
    assert profile["count"] == 1
    assert profile["driver"] == "GTiff"
    assert tuple(data.shape) == (6, 8)
    assert bool(np.array_equal(data, grid.array, equal_nan=True))
    assert bool((mask == 255).all())


def test_absolute_export(tmp_path: Path) -> None:
    grid = absolute_grid(tmp_path)
    target = tmp_path / "abs.tif"
    result = export_geotiff(grid, target)
    assert result.verified is True
    assert (result.width, result.height) == (5, 4)
    data, _, _ = read_all(target)
    assert bool(np.array_equal(data, grid.array, equal_nan=True))


def test_tags_serialized(tmp_path: Path) -> None:
    import warnings

    import rasterio
    from rasterio.errors import NotGeoreferencedWarning

    grid = agl_grid(tmp_path)
    target = tmp_path / "dsm.tif"
    export_geotiff(grid, target)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.open(target) as dataset:
            tags = dataset.tags(ns="depthwizard")
    assert tags["semantics"] == "height_agl_ndsm"
    assert tags["units"] == "meters"
    assert tags["model_name"] == "synthetic-depth"
    assert tags["calibration_method"] == "scale_offset"
    assert tags["calibration_reference"] == "ref-s10"
    assert tags["source_checksum"] == grid.source_checksum


def test_rejects_non_grid() -> None:
    with pytest.raises(TypeError, match="DSMGrid"):
        export_geotiff("not-a-grid", "out.tif")  # type: ignore[arg-type]


def test_rejects_grids_bypassing_invariants(tmp_path: Path) -> None:
    grid = agl_grid(tmp_path)
    rotten_array = grid.array.copy()
    rotten_array[0, 0] = float("inf")  # non-finite under a valid mask
    rotten = grid.model_copy(update={"array": rotten_array})
    with pytest.raises(ExportError, match="invariant violated"):
        export_geotiff(rotten, tmp_path / "rotten.tif")
    assert isinstance(grid, DSMGrid)
