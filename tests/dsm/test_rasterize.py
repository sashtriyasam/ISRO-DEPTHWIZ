"""Basic conversion: shape, ordering, dtype, meaning, determinism."""

import math
from pathlib import Path

import numpy as np
import pytest

from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.dsm import (
    NODATA,
    DSMGrid,
    RasterizeOptions,
    ResamplingPolicy,
    rasterize_height_product,
)
from tests.dsm.support import absolute_geotiff_product, agl_png_product


def test_agl_conversion(tmp_path: Path) -> None:
    product, _, _ = agl_png_product(tmp_path)
    grid = rasterize_height_product(product)
    assert isinstance(grid, DSMGrid)
    assert (grid.width, grid.height) == (8, 6)
    assert grid.array.shape == (6, 8)
    assert grid.dtype == "float32"
    assert str(grid.array.dtype) == "float32"
    assert grid.units == "meters"
    assert grid.semantics is ElevationSemantics.HEIGHT_AGL_NDSM
    assert grid.resampling is ResamplingPolicy.NO_RESAMPLING
    assert grid.invalid_count == 0
    assert bool((grid.valid_mask).all())
    assert math.isnan(grid.nodata)
    # Row-major mapping preserved (float32 precision).
    for row in (0, 2, 5):
        for col in (0, 3, 7):
            assert grid.array[row, col] == pytest.approx(
                product.values[row * 8 + col], rel=1e-6, abs=1e-6
            )


def test_nodata_constant_documented() -> None:
    assert math.isnan(NODATA)  # NaN marker by definition


def test_absolute_conversion(tmp_path: Path) -> None:
    product, _, _ = absolute_geotiff_product(tmp_path)
    grid = rasterize_height_product(product)
    assert grid.semantics is ElevationSemantics.ABSOLUTE_ELEVATION_DSM
    assert (grid.width, grid.height) == (5, 4)
    assert grid.array.shape == (4, 5)


def test_float64_preserves_full_precision(tmp_path: Path) -> None:
    product, _, _ = agl_png_product(tmp_path)
    grid = rasterize_height_product(product, RasterizeOptions(dtype="float64"))
    assert grid.dtype == "float64"
    assert tuple(grid.array.ravel().tolist()) == product.values


def test_metadata_passthrough(tmp_path: Path) -> None:
    product, depth, calibration = agl_png_product(tmp_path)
    grid = rasterize_height_product(product)
    assert grid.depth_model_name == depth.model_name == "synthetic-depth"
    assert grid.source_input_id == product.source_input_id
    assert grid.source_checksum == product.source_checksum
    assert grid.calibration_method == "scale_offset"
    assert grid.calibration_reference == calibration.reference_id
    assert (grid.calibration_scale, grid.calibration_offset) == (2.5, 10.0)
    assert grid.calibration_valid_samples == calibration.valid_samples
    assert grid.provenance == product.provenance


def test_rejects_non_product() -> None:
    with pytest.raises(TypeError, match="ScientificHeightProduct"):
        rasterize_height_product("not-a-product")  # type: ignore[arg-type]


def test_determinism(tmp_path: Path) -> None:
    product, _, _ = agl_png_product(tmp_path)
    first = rasterize_height_product(product)
    second = rasterize_height_product(product)
    assert np.array_equal(first.array, second.array, equal_nan=True)
    assert np.array_equal(first.valid_mask, second.valid_mask)
    # Pydantic == cannot compare ndarray fields elementwise, so metadata
    # equality is asserted on the array-free dump.
    assert first.model_dump(exclude={"array", "valid_mask"}) == second.model_dump(
        exclude={"array", "valid_mask"}
    )
