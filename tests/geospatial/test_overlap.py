"""Overlap geometry: containment, partial, disjoint, edge-touch, cross-CRS."""

import pytest

from depthwizard.contracts.spatial import Bounds
from depthwizard.errors import MissingCRSError
from depthwizard.geospatial.overlap import calculate_overlap
from tests.geospatial.support import CRS_UTM, CRS_WGS84


def _box(min_x: float, min_y: float, max_x: float, max_y: float) -> Bounds:
    return Bounds(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)


def test_partial_overlap() -> None:
    result = calculate_overlap(
        _box(100.0, 198.0, 102.5, 200.0),
        CRS_UTM,
        _box(101.0, 199.0, 103.0, 201.0),
        CRS_UTM,
    )
    assert result.intersects is True
    assert result.bounds is not None
    assert (result.bounds.min_x, result.bounds.min_y) == (101.0, 199.0)
    assert (result.bounds.max_x, result.bounds.max_y) == (102.5, 200.0)
    assert result.crs == CRS_UTM
    assert result.area == pytest.approx(1.5 * 1.0)
    assert result.fraction_of_first == pytest.approx(1.5 / 5.0)
    assert result.fraction_of_second == pytest.approx(1.5 / 4.0)


def test_full_containment() -> None:
    result = calculate_overlap(
        _box(0.0, 0.0, 10.0, 10.0),
        CRS_UTM,
        _box(2.0, 3.0, 4.0, 5.0),
        CRS_UTM,
    )
    assert result.intersects is True
    assert result.area == pytest.approx(4.0)
    assert result.fraction_of_first == pytest.approx(0.04)
    assert result.fraction_of_second == pytest.approx(1.0)


def test_disjoint() -> None:
    result = calculate_overlap(
        _box(0.0, 0.0, 1.0, 1.0),
        CRS_UTM,
        _box(2.0, 2.0, 3.0, 3.0),
        CRS_UTM,
    )
    assert result.intersects is False
    assert result.bounds is None
    assert result.area == 0.0
    assert result.fraction_of_first == 0.0
    assert result.fraction_of_second == 0.0


def test_edge_touch_is_not_intersection() -> None:
    # Shared edge, zero shared area: no pixels in common.
    result = calculate_overlap(
        _box(0.0, 0.0, 1.0, 1.0),
        CRS_UTM,
        _box(1.0, 0.0, 2.0, 1.0),
        CRS_UTM,
    )
    assert result.intersects is False
    assert result.bounds is None


def test_missing_crs_refused() -> None:
    with pytest.raises(MissingCRSError, match="requires a CRS"):
        calculate_overlap(_box(0, 0, 1, 1), None, _box(0, 0, 1, 1), CRS_UTM)
    with pytest.raises(MissingCRSError, match="requires a CRS"):
        calculate_overlap(_box(0, 0, 1, 1), CRS_UTM, _box(0, 0, 1, 1), None)


def test_cross_crs_same_coverage() -> None:
    from rasterio.crs import CRS
    from rasterio.warp import transform_bounds

    # Same geographic square expressed in two systems (derived at runtime,
    # not hard-coded): overlap must be found in the first frame.
    lon0, lat0, lon1, lat1 = 78.0, 12.0, 78.1, 12.1
    east0, north0, east1, north1 = transform_bounds(
        CRS.from_string(CRS_WGS84), CRS.from_string(CRS_UTM), lon0, lat0, lon1, lat1
    )
    result = calculate_overlap(
        _box(lon0, lat0, lon1, lat1),
        CRS_WGS84,
        _box(east0, north0, east1, north1),
        CRS_UTM,
    )
    assert result.intersects is True
    assert result.crs == CRS_WGS84
    assert result.fraction_of_first == pytest.approx(1.0, abs=1e-6)
    # Densified-edge reprojection bulges the returned box slightly, so
    # the second fraction is near (not exactly) unity by construction.
    assert 0.9 < result.fraction_of_second <= 1.0


def test_cross_crs_disjoint() -> None:
    result = calculate_overlap(
        _box(78.0, 12.0, 78.1, 12.1),
        CRS_WGS84,
        _box(100.0, 198.0, 102.5, 200.0),
        CRS_UTM,
    )
    assert result.intersects is False
