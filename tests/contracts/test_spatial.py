"""Deterministic tests for the spatial metadata contract."""

import pytest
from pydantic import ValidationError

from depthwizard.contracts.spatial import (
    AffineTransform,
    Bounds,
    SpatialContext,
    SpatialDetails,
    SpatialKind,
)


def test_absent_spatial_without_fake_values() -> None:
    for kind in (SpatialKind.UNAVAILABLE, SpatialKind.NOT_APPLICABLE):
        ctx = SpatialContext(kind=kind)
        assert ctx.details is None


def test_non_present_kind_must_not_carry_details() -> None:
    with pytest.raises(ValidationError):
        SpatialContext(
            kind=SpatialKind.NOT_APPLICABLE,
            details=SpatialDetails(crs="EPSG:4326"),
        )


def test_present_requires_details() -> None:
    with pytest.raises(ValidationError):
        SpatialContext(kind=SpatialKind.PRESENT)
    with pytest.raises(ValidationError):
        SpatialContext(kind=SpatialKind.PRESENT, details=SpatialDetails())


def test_present_accepts_crs_only() -> None:
    ctx = SpatialContext(kind=SpatialKind.PRESENT, details=SpatialDetails(crs="EPSG:4326"))
    assert ctx.details is not None and ctx.details.crs == "EPSG:4326"
    assert ctx.details.transform is None  # unknown stays unknown


def test_bounds_rejects_inverted_ranges() -> None:
    with pytest.raises(ValidationError):
        Bounds(min_x=5.0, min_y=0.0, max_x=1.0, max_y=1.0)


def test_affine_roundtrip() -> None:
    t = AffineTransform(a=10.0, b=0.5, c=0.0, d=20.0, e=0.0, f=-0.5)
    assert t.as_tuple() == (10.0, 0.5, 0.0, 20.0, 0.0, -0.5)
