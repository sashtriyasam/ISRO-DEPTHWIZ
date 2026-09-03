"""Pixel/world conversions, anchors, singular and non-finite guards."""

import pytest

from depthwizard.errors import GeospatialProcessingError
from depthwizard.geospatial.transforms import (
    PixelAnchor,
    pixel_to_world,
    require_invertible,
    transform_determinant,
    world_to_pixel,
)
from tests.geospatial.support import NORTH_UP, ROTATED, SINGULAR, SOUTH_UP


def test_center_convention() -> None:
    # Pixel (0, 0) center: (100 + 0.5*0.5, 200 - 0.5*0.5).
    assert pixel_to_world(NORTH_UP, 0, 0) == pytest.approx((100.25, 199.75))
    assert pixel_to_world(NORTH_UP, 0, 0, PixelAnchor.CENTER) == pytest.approx((100.25, 199.75))


def test_corner_convention_distinct() -> None:
    assert pixel_to_world(NORTH_UP, 0, 0, PixelAnchor.CORNER) == pytest.approx((100.0, 200.0))
    assert pixel_to_world(NORTH_UP, 4, 3, PixelAnchor.CORNER) == pytest.approx((102.0, 198.5))


def test_round_trip() -> None:
    for col, row in ((0, 0), (2, 1), (4, 3)):
        x, y = pixel_to_world(NORTH_UP, col, row, PixelAnchor.CORNER)
        back_col, back_row = world_to_pixel(NORTH_UP, x, y)
        assert (back_col, back_row) == pytest.approx((col, row), abs=1e-9)
    # Center mapping is offset by half a pixel by definition.
    x, y = pixel_to_world(NORTH_UP, 2, 1)
    back_col, back_row = world_to_pixel(NORTH_UP, x, y)
    assert (back_col, back_row) == pytest.approx((2.5, 1.5), abs=1e-9)


def test_south_up() -> None:
    assert pixel_to_world(SOUTH_UP, 1, 2) == pytest.approx((13.0, 25.0))
    x, y = pixel_to_world(SOUTH_UP, 1, 2, PixelAnchor.CORNER)
    assert (x, y) == pytest.approx((12.0, 24.0))
    col, row = world_to_pixel(SOUTH_UP, x, y)
    assert (col, row) == pytest.approx((1.0, 2.0), abs=1e-12)


def test_rotated_transform() -> None:
    x, y = pixel_to_world(ROTATED, 1, 1, PixelAnchor.CORNER)
    assert (x, y) == pytest.approx((1.5, 0.5))
    col, row = world_to_pixel(ROTATED, x, y)
    assert (col, row) == pytest.approx((1.0, 1.0), abs=1e-12)


def test_determinant() -> None:
    assert transform_determinant(NORTH_UP) == pytest.approx(-0.25)
    assert transform_determinant(SINGULAR) == 0.0


def test_singular_inverse_fails() -> None:
    with pytest.raises(GeospatialProcessingError, match="singular"):
        require_invertible(SINGULAR)
    with pytest.raises(GeospatialProcessingError, match="singular"):
        world_to_pixel(SINGULAR, 0.0, 0.0)
    # Forward mapping needs no inverse and still works.
    assert pixel_to_world(SINGULAR, 0, 0) == pytest.approx((1.5, 3.0))


def test_nonfinite_transform_rejected() -> None:
    from depthwizard.contracts.spatial import AffineTransform

    bad = AffineTransform(a=float("nan"), b=1.0, c=0.0, d=0.0, e=0.0, f=1.0)
    with pytest.raises(GeospatialProcessingError, match="finite"):
        pixel_to_world(bad, 0, 0)
    with pytest.raises(GeospatialProcessingError, match="finite"):
        require_invertible(bad)
