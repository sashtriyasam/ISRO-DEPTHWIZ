"""Tests for local UTM projection helper."""

from __future__ import annotations

import pytest

from depthwizard.contracts.spatial import AffineTransform, Bounds, SpatialDetails
from depthwizard.geospatial.projection import projected_metric_details, resolve_local_utm_crs


def test_resolve_local_utm_crs_known_locations() -> None:
    """Resolves correct UTM EPSG codes for known coordinates."""
    # Delhi / India (77.2°E, 28.6°N) -> Zone 43N (EPSG:32643)
    assert resolve_local_utm_crs(77.2, 28.6) == "EPSG:32643"
    # Washington DC (77.0°W, 38.9°N) -> Zone 18N (EPSG:32618)
    assert resolve_local_utm_crs(-77.0, 38.9) == "EPSG:32618"
    # Southern Hemisphere location (-60.0°W, -33.0°S) -> Zone 21S (EPSG:32721)
    assert resolve_local_utm_crs(-60.0, -33.0) == "EPSG:32721"


def test_resolve_local_utm_crs_out_of_bounds() -> None:
    """Out of range longitude/latitude raises ValueError."""
    with pytest.raises(ValueError, match="longitude out of range"):
        resolve_local_utm_crs(190.0, 0.0)
    with pytest.raises(ValueError, match="latitude out of WGS84 UTM bounds"):
        resolve_local_utm_crs(0.0, 89.0)


def test_projected_metric_details_passthrough_utm() -> None:
    """Already projected UTM details are returned unchanged."""
    details = SpatialDetails(
        crs="EPSG:32643",
        transform=AffineTransform(a=0.5, b=0.0, c=100.0, d=0.0, e=-0.5, f=200.0),
        bounds=Bounds(min_x=100.0, min_y=100.0, max_x=200.0, max_y=200.0),
    )
    result = projected_metric_details(details)
    assert result == details


def test_projected_metric_details_converts_geographic() -> None:
    """Geographic WGS84 details are transformed into metric local UTM representation."""
    details = SpatialDetails(
        crs="EPSG:4326",
        transform=AffineTransform(a=0.0001, b=0.0, c=77.0, d=0.0, e=-0.0001, f=28.0),
        bounds=Bounds(min_x=77.0, min_y=27.9, max_x=77.1, max_y=28.0),
    )
    result = projected_metric_details(details)
    assert "EPSG:3264" in str(result.crs)
    assert result.transform is not None
    assert abs(result.transform.a) > 1.0  # Converted to metres (~10m)
