"""Sampling: pixel-exact, world-mapped, OOB/nodata invalid, no rounding."""

from pathlib import Path

import pytest

from depthwizard.dem.build import build_terrain_reference
from depthwizard.dem.sample import sample_terrain, sample_terrain_at_world
from tests.dem.support import dem_inspection, image_target, native_grid


def test_pixel_exact(tmp_path: Path) -> None:
    grid = native_grid(tmp_path)
    sample = sample_terrain(grid, 0, 2)
    assert sample.valid is True
    assert sample.elevation == 102.0
    assert (sample.row, sample.col) == (0, 2)
    assert (sample.pixel_row, sample.pixel_col) == (0.0, 2.0)
    assert sample.units == "meters"
    assert sample.reference_id == "dem.tif"


def test_pixel_zero_valid_nodata_invalid(tmp_path: Path) -> None:
    grid = native_grid(tmp_path)
    zero = sample_terrain(grid, 0, 0)
    assert zero.valid is True
    assert zero.elevation == 0.0
    hole = sample_terrain(grid, 1, 1)
    assert hole.valid is False
    assert hole.elevation is None
    assert (hole.row, hole.col) == (1, 1)


def test_out_of_bounds_invalid(tmp_path: Path) -> None:
    grid = native_grid(tmp_path)
    for row, col in ((-1, 0), (0, -1), (5, 0), (0, 6), (99, 99)):
        sample = sample_terrain(grid, row, col)
        assert sample.valid is False
        assert sample.elevation is None


def test_pixel_type_policy(tmp_path: Path) -> None:
    grid = native_grid(tmp_path)
    with pytest.raises(TypeError, match="integer row/col"):
        sample_terrain(grid, 1.5, 2)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="integer row/col"):
        sample_terrain(grid, True, 2)


def test_world_sampling(tmp_path: Path) -> None:
    grid = native_grid(tmp_path)
    # Native DEM cell (0, 2) center: x = 99 + 2.5, y = 201 - 0.5.
    sample = sample_terrain_at_world(grid, 101.5, 200.5)
    assert sample.valid is True
    assert (sample.row, sample.col) == (0, 2)
    assert sample.elevation == 102.0
    assert (sample.x, sample.y) == (101.5, 200.5)
    assert sample.pixel_col == pytest.approx(2.5)
    assert sample.pixel_row == pytest.approx(0.5)


def test_world_out_of_bounds(tmp_path: Path) -> None:
    grid = native_grid(tmp_path)
    sample = sample_terrain_at_world(grid, -1000.0, -1000.0)
    assert sample.valid is False
    assert sample.elevation is None
    assert (sample.x, sample.y) == (-1000.0, -1000.0)


def test_world_nodata_location(tmp_path: Path) -> None:
    grid = native_grid(tmp_path)
    # Native DEM cell (1, 1) center: x = 100.5, y = 199.5.
    sample = sample_terrain_at_world(grid, 100.5, 199.5)
    assert sample.valid is False
    assert sample.elevation is None
    assert (sample.row, sample.col) == (1, 1)


def test_world_rejects_nonfinite(tmp_path: Path) -> None:
    grid = native_grid(tmp_path)
    with pytest.raises(TypeError, match="finite"):
        sample_terrain_at_world(grid, float("nan"), 0.0)


def test_aligned_world_sampling(tmp_path: Path) -> None:
    inspection = dem_inspection(tmp_path)
    grid = build_terrain_reference(inspection, image_target(tmp_path))
    # Aligned image-grid cell (0, 2) center: x = 101.25, y = 199.75.
    sample = sample_terrain_at_world(grid, 101.25, 199.75)
    assert sample.valid is True
    assert (sample.row, sample.col) == (0, 2)
    assert sample.elevation == 108.0
