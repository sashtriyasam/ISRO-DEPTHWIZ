"""Nodata/mask fidelity: valid zero vs invalid, infinity never valid."""

import math
from pathlib import Path

import numpy as np

from depthwizard.dsm import rasterize_height_product
from depthwizard.export import export_geotiff
from tests.dsm.support import agl_png_product
from tests.export.support import read_all


def test_zero_valid_nan_invalid(tmp_path: Path) -> None:
    product, _, _ = agl_png_product(tmp_path)
    values = list(product.values)
    values[0] = 0.0
    values[1] = float("nan")
    grid = rasterize_height_product(product.model_copy(update={"values": tuple(values)}))
    target = tmp_path / "nodata.tif"
    export_geotiff(grid, target)
    data, mask, _ = read_all(target)
    assert data.ravel()[0] == 0.0
    assert mask.ravel()[0] == 255
    assert math.isnan(data.ravel()[1])
    assert mask.ravel()[1] == 0
    assert grid.invalid_count == 1


def test_infinity_never_serialized_valid(tmp_path: Path) -> None:
    product, _, _ = agl_png_product(tmp_path)
    values = list(product.values)
    values[2] = float("inf")
    grid = rasterize_height_product(product.model_copy(update={"values": tuple(values)}))
    target = tmp_path / "inf.tif"
    export_geotiff(grid, target)
    data, mask, _ = read_all(target)
    assert mask.ravel()[2] == 0
    assert math.isnan(data.ravel()[2])
    assert np.isfinite(data[grid.valid_mask]).all()


def test_mask_matches_grid_valid_mask(tmp_path: Path) -> None:
    from tests.export.support import agl_grid

    grid = agl_grid(tmp_path)
    target = tmp_path / "dsm.tif"
    export_geotiff(grid, target)
    _, mask, _ = read_all(target)
    expected = (grid.valid_mask.astype("uint8")) * 255
    assert bool((mask == expected).all())
