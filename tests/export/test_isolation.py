"""Compression policy and export isolation guarantees."""

from pathlib import Path

import numpy as np

from depthwizard.export import Compression, ExportOptions, export_geotiff
from tests.export.support import agl_grid, read_all


def test_deflate_default_verified(tmp_path: Path) -> None:
    grid = agl_grid(tmp_path)
    target = tmp_path / "dsm.tif"
    result = export_geotiff(grid, target)
    assert result.compression == "deflate"
    _, _, profile = read_all(target)
    assert profile.get("compress") == "deflate"


def test_uncompressed_option_round_trips(tmp_path: Path) -> None:
    grid = agl_grid(tmp_path)
    target = tmp_path / "plain.tif"
    result = export_geotiff(grid, target, ExportOptions(compression=Compression.NONE))
    assert result.compression == "none"
    assert result.verified is True
    _, _, profile = read_all(target)
    assert profile.get("compress") is None
    data, _, _ = read_all(target)
    assert tuple(data.shape) == (6, 8)


def test_double_export_equivalent(tmp_path: Path) -> None:
    grid = agl_grid(tmp_path)
    first = tmp_path / "a.tif"
    second = tmp_path / "b.tif"
    export_geotiff(grid, first)
    export_geotiff(grid, second)
    data_a, mask_a, _ = read_all(first)
    data_b, mask_b, _ = read_all(second)
    assert bool(np.array_equal(data_a, data_b, equal_nan=True))
    assert bool((mask_a == mask_b).all())


def test_source_grid_unchanged(tmp_path: Path) -> None:
    grid = agl_grid(tmp_path)
    array_before = grid.array.copy()
    mask_before = grid.valid_mask.copy()
    export_geotiff(grid, tmp_path / "dsm.tif")
    assert bool(np.array_equal(grid.array, array_before, equal_nan=True))
    assert bool((grid.valid_mask == mask_before).all())
