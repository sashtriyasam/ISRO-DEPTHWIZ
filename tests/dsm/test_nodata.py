"""Nodata policy: valid 0.0 stays valid; non-finite becomes masked NaN."""

import math
from pathlib import Path

import numpy as np
import pytest

from depthwizard.dsm import rasterize_height_product
from depthwizard.errors import InvalidInputError
from tests.dsm.support import agl_png_product


def test_mixed_valid_and_invalid(tmp_path: Path) -> None:
    product, _, _ = agl_png_product(tmp_path)
    poisoned = list(product.values)
    poisoned[0] = 0.0  # valid zero must remain valid
    poisoned[1] = float("nan")
    poisoned[2] = float("inf")
    poisoned[3] = float("-inf")
    mixed = product.model_copy(update={"values": tuple(poisoned)})
    grid = rasterize_height_product(mixed)
    assert grid.invalid_count == 3
    assert grid.valid_mask.ravel()[0]
    assert not grid.valid_mask.ravel()[1]
    assert not grid.valid_mask.ravel()[2]
    assert not grid.valid_mask.ravel()[3]
    assert grid.array.ravel()[0] == 0.0
    for index in (1, 2, 3):
        assert math.isnan(grid.array.ravel()[index])
    assert grid.array.ravel()[0] == pytest.approx(mixed.values[0], rel=1e-6)


def test_partial_float32_overflow_masked(tmp_path: Path) -> None:
    product, _, _ = agl_png_product(tmp_path)
    poisoned = [1.0] * len(product.values)
    poisoned[5] = 1e308  # finite in float64, inf in float32
    mixed = product.model_copy(update={"values": tuple(poisoned)})
    grid = rasterize_height_product(mixed)
    assert grid.invalid_count == 1
    assert not grid.valid_mask.ravel()[5]
    assert math.isnan(grid.array.ravel()[5])
    assert grid.array.ravel()[0] == pytest.approx(1.0)


def test_all_invalid_fails_explicitly(tmp_path: Path) -> None:
    product, _, _ = agl_png_product(tmp_path)
    count = len(product.values)
    rotten = product.model_copy(update={"values": (float("nan"),) * count})
    with pytest.raises(InvalidInputError, match=f"all {count}"):
        rasterize_height_product(rotten)


def test_all_invalid_via_overflow_fails(tmp_path: Path) -> None:
    product, _, _ = agl_png_product(tmp_path)
    huge = product.model_copy(update={"values": (1e308,) * len(product.values)})
    with pytest.raises(InvalidInputError, match="all"):
        rasterize_height_product(huge)


def test_invalid_count_consistent(tmp_path: Path) -> None:
    product, _, _ = agl_png_product(tmp_path)
    grid = rasterize_height_product(product)
    assert grid.invalid_count == 0
    assert grid.valid_mask.dtype.kind == "b"
    assert isinstance(grid.array, np.ndarray)
