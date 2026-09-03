"""Ownership: grids own their arrays; sources never mutated."""

from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from depthwizard.dsm import rasterize_height_product
from tests.dsm.support import agl_png_product


def test_grids_are_independent(tmp_path: Path) -> None:
    product, _, _ = agl_png_product(tmp_path)
    first = rasterize_height_product(product)
    second = rasterize_height_product(product)
    first.array[0, 0] = -12345.0
    first.valid_mask[0, 0] = False
    assert second.array[0, 0] != -12345.0
    assert second.valid_mask[0, 0]
    assert np.isfinite(second.array).all()


def test_source_product_unchanged(tmp_path: Path) -> None:
    product, _, calibration = agl_png_product(tmp_path)
    product_before = product.model_copy(deep=True)
    rasterize_height_product(product)
    assert product == product_before
    assert calibration.scale == 2.5


def test_grid_model_frozen(tmp_path: Path) -> None:
    product, _, _ = agl_png_product(tmp_path)
    grid = rasterize_height_product(product)
    with pytest.raises(ValidationError):
        grid.width = 999
