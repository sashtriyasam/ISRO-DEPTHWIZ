"""Bounds derivation, CRS validation/equality, grid compatibility."""

import pytest

from depthwizard.contracts.spatial import (
    SpatialContext,
    SpatialDetails,
    SpatialKind,
)
from depthwizard.errors import GeospatialProcessingError, MissingCRSError
from depthwizard.geospatial.crs import crs_equal, parse_crs, require_crs
from depthwizard.geospatial.grids import (
    AlignmentStatus,
    TargetGrid,
    check_grid_compatibility,
    classify_alignment,
)
from depthwizard.geospatial.transforms import raster_bounds
from tests.geospatial.support import CRS_UTM, NORTH_UP, SOUTH_UP, utm_grid


def test_bounds_north_up() -> None:
    bounds = raster_bounds(NORTH_UP, 5, 4)
    assert (bounds.min_x, bounds.min_y) == (100.0, 198.0)
    assert (bounds.max_x, bounds.max_y) == (102.5, 200.0)


def test_bounds_south_up_no_axis_assumption() -> None:
    bounds = raster_bounds(SOUTH_UP, 5, 4)
    assert (bounds.min_x, bounds.min_y) == (10.0, 20.0)
    assert (bounds.max_x, bounds.max_y) == (20.0, 28.0)


def test_bounds_rotated() -> None:
    from tests.geospatial.support import ROTATED

    bounds = raster_bounds(ROTATED, 5, 4)
    assert (bounds.min_x, bounds.min_y) == (0.0, -2.5)
    assert (bounds.max_x, bounds.max_y) == (7.0, 4.0)


def test_bounds_bad_dimensions() -> None:
    with pytest.raises(GeospatialProcessingError, match="positive"):
        raster_bounds(NORTH_UP, 0, 4)


def test_valid_crs_accepted() -> None:
    crs = parse_crs(CRS_UTM)
    assert crs.to_string() == CRS_UTM


def test_equivalent_crs_compare_equal() -> None:
    from rasterio.crs import CRS

    wkt = CRS.from_string(CRS_UTM).to_wkt()
    assert wkt != CRS_UTM
    assert crs_equal(CRS_UTM, wkt) is True
    assert crs_equal(CRS_UTM, "EPSG:4326") is False


def test_invalid_crs_fails() -> None:
    with pytest.raises(GeospatialProcessingError, match="invalid CRS"):
        parse_crs("not-a-crs-at-all")
    with pytest.raises(GeospatialProcessingError, match="invalid CRS"):
        crs_equal("not-a-crs-at-all", CRS_UTM)


def test_require_crs_present_and_missing() -> None:
    present = SpatialContext(kind=SpatialKind.PRESENT, details=SpatialDetails(crs=CRS_UTM))
    assert require_crs(present, "test-op") == CRS_UTM
    with pytest.raises(MissingCRSError, match="requires a CRS"):
        require_crs(SpatialContext(kind=SpatialKind.UNAVAILABLE), "test-op")
    with pytest.raises(MissingCRSError, match="requires a CRS"):
        require_crs(SpatialContext(kind=SpatialKind.NOT_APPLICABLE), "test-op")


def test_compatible_grids() -> None:
    result = check_grid_compatibility(utm_grid(), utm_grid())
    assert result.compatible is True
    assert result.reasons == ()
    assert classify_alignment(utm_grid(), utm_grid()) is AlignmentStatus.COMPATIBLE


def test_incompatible_dimensions() -> None:
    result = check_grid_compatibility(utm_grid(5, 4), utm_grid(6, 4))
    assert result.compatible is False
    assert any("dimensions" in reason for reason in result.reasons)


def test_incompatible_crs() -> None:
    other = TargetGrid(
        crs="EPSG:4326",
        transform=utm_grid().transform,
        width=5,
        height=4,
        dtype="float32",
        nodata=float("nan"),
    )
    result = check_grid_compatibility(utm_grid(), other)
    assert result.compatible is False
    assert any("CRS" in reason for reason in result.reasons)
    assert classify_alignment(utm_grid(), other) is AlignmentStatus.REPROJECTABLE


def test_incompatible_transform() -> None:
    from depthwizard.contracts.spatial import AffineTransform

    shifted = utm_grid().model_copy(
        update={"transform": AffineTransform(a=101.0, b=0.5, c=0.0, d=200.0, e=0.0, f=-0.5)}
    )
    result = check_grid_compatibility(utm_grid(), shifted)
    assert result.compatible is False
    assert any("affine" in reason for reason in result.reasons)
    assert classify_alignment(utm_grid(), shifted) is AlignmentStatus.REPROJECTABLE


def test_incompatible_resolution() -> None:
    coarse = utm_grid().model_copy(update={"resolution": 1.0})
    result = check_grid_compatibility(utm_grid(), coarse)
    assert result.compatible is False
    assert any("resolution" in reason for reason in result.reasons)


def test_invalid_crs_incompatible() -> None:
    bogus = utm_grid().model_copy(update={"crs": "not-a-crs-at-all"})
    result = check_grid_compatibility(utm_grid(), bogus)
    assert result.compatible is False
    assert any("invalid CRS" in reason for reason in result.reasons)
    assert classify_alignment(utm_grid(), bogus) is AlignmentStatus.INCOMPATIBLE
