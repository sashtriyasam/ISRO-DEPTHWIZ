"""Reprojection, resampling, alignment, nodata, dtype, determinism."""

import numpy as np
import pytest

from depthwizard.errors import GeospatialProcessingError
from depthwizard.geospatial.grids import TargetGrid
from depthwizard.geospatial.warp import (
    ReprojectedRaster,
    ResamplingMethod,
    align_raster,
    reproject_array,
)
from tests.geospatial.support import (
    CRS_UTM,
    assert_grids_equal,
    ramp_array,
    utm_grid,
    wgs84_target_from_utm,
)


def test_same_grid_nearest_round_trip() -> None:
    grid = utm_grid(5, 4)
    source = ramp_array(5, 4)
    result = reproject_array(
        source,
        CRS_UTM,
        grid.transform,
        grid,
        source_nodata=float("nan"),
        resampling=ResamplingMethod.NEAREST,
    )
    assert isinstance(result, ReprojectedRaster)
    assert result.array.shape == (4, 5)
    assert result.array.dtype == np.dtype("float32")
    assert bool(np.array_equal(result.array, source))
    assert bool(result.valid_mask.all())
    assert_grids_equal(result.grid, grid)
    assert result.source_crs == CRS_UTM


def test_cross_crs_reprojection() -> None:
    grid = utm_grid(8, 6)
    source = ramp_array(8, 6)
    target = wgs84_target_from_utm(8, 6)
    result = reproject_array(
        source,
        CRS_UTM,
        grid.transform,
        target,
        source_nodata=float("nan"),
        resampling=ResamplingMethod.NEAREST,
    )
    assert result.array.shape == (target.height, target.width)
    assert result.array.dtype == np.dtype("float32")
    assert_grids_equal(result.grid, target)
    assert result.source_crs == CRS_UTM
    assert bool(np.isfinite(result.array[result.valid_mask]).all())
    assert int(result.valid_mask.sum()) > 0


def test_bilinear_continuous_field() -> None:
    grid = utm_grid(8, 6)
    source = ramp_array(8, 6)
    result = reproject_array(
        source,
        CRS_UTM,
        grid.transform,
        grid,
        source_nodata=float("nan"),
        resampling=ResamplingMethod.BILINEAR,
    )
    assert result.array.shape == (6, 8)
    assert bool(result.valid_mask.all())
    assert bool(np.isfinite(result.array).all())


def test_nodata_preserved() -> None:
    grid = utm_grid(4, 4)
    source = ramp_array(4, 4)
    source[0, 0] = 0.0  # valid zero stays valid
    source[1, 1] = float("nan")
    source[2, 3] = float("nan")
    result = reproject_array(
        source,
        CRS_UTM,
        grid.transform,
        grid,
        source_nodata=float("nan"),
        resampling=ResamplingMethod.NEAREST,
    )
    assert result.array[0, 0] == 0.0
    assert result.valid_mask[0, 0]
    assert not result.valid_mask[1, 1]
    assert not result.valid_mask[2, 3]
    assert bool(np.isnan(result.array[~result.valid_mask]).all())
    assert int((~result.valid_mask).sum()) == 2


def test_float64_dtype_preserved() -> None:
    grid = utm_grid(4, 4, dtype="float64")
    source = ramp_array(4, 4, dtype="float64")
    result = reproject_array(
        source,
        CRS_UTM,
        grid.transform,
        grid,
        source_nodata=float("nan"),
        resampling=ResamplingMethod.NEAREST,
    )
    assert result.array.dtype == np.dtype("float64")
    assert bool(np.array_equal(result.array, source))


def test_int_source_rejected() -> None:
    grid = utm_grid(4, 4)
    with pytest.raises(GeospatialProcessingError, match="floating point"):
        reproject_array(np.ones((4, 4), dtype=np.int32), CRS_UTM, grid.transform, grid)


def test_missing_source_crs_rejected() -> None:
    grid = utm_grid(4, 4)
    with pytest.raises(GeospatialProcessingError, match="invalid CRS"):
        reproject_array(ramp_array(4, 4), "not-a-crs", grid.transform, grid)


def test_align_identical_copies() -> None:
    grid = utm_grid(5, 4)
    source = ramp_array(5, 4)
    result = align_raster(source, grid, utm_grid(5, 4))
    assert bool(np.array_equal(result.array, source))
    assert_grids_equal(result.grid, utm_grid(5, 4))
    assert result.array is not source


def test_align_reprojects() -> None:
    grid = utm_grid(8, 6)
    source = ramp_array(8, 6)
    target = wgs84_target_from_utm(8, 6)
    result = align_raster(source, grid, target)
    assert result.array.shape == (target.height, target.width)
    assert result.source_crs == CRS_UTM


def test_align_shape_mismatch_rejected() -> None:
    grid = utm_grid(5, 4)
    with pytest.raises(GeospatialProcessingError, match="shape"):
        align_raster(np.ones((2, 2), dtype=np.float32), grid, utm_grid(5, 4))


def test_source_untouched() -> None:
    grid = utm_grid(5, 4)
    source = ramp_array(5, 4)
    snapshot = source.copy()
    target = wgs84_target_from_utm(5, 4)
    reproject_array(source, CRS_UTM, grid.transform, target)
    align_raster(source, grid, grid)
    assert bool(np.array_equal(source, snapshot))


def test_determinism() -> None:
    grid = utm_grid(8, 6)
    source = ramp_array(8, 6)
    target = wgs84_target_from_utm(8, 6)
    first = reproject_array(source, CRS_UTM, grid.transform, target)
    second = reproject_array(source, CRS_UTM, grid.transform, target)
    assert bool(np.array_equal(first.array, second.array, equal_nan=True))
    assert bool((first.valid_mask == second.valid_mask).all())


def test_nongeoreferenced_local_ops() -> None:
    # Pixel-space conversions need no CRS at all.
    from depthwizard.contracts.spatial import AffineTransform
    from depthwizard.geospatial.transforms import pixel_to_world

    local = AffineTransform(a=0.0, b=1.0, c=0.0, d=0.0, e=0.0, f=1.0)
    assert pixel_to_world(local, 2, 3) == (2.5, 3.5)


def test_target_grid_requires_crs() -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        TargetGrid(
            crs="",
            transform=utm_grid().transform,
            width=2,
            height=2,
            dtype="float32",
            nodata=float("nan"),
        )
