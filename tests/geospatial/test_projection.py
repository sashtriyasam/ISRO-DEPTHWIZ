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
        transform=AffineTransform(a=100.0, b=0.5, c=0.0, d=200.0, e=0.0, f=-0.5),
        bounds=Bounds(min_x=100.0, min_y=100.0, max_x=200.0, max_y=200.0),
    )
    result = projected_metric_details(details)
    assert result == details


def test_projected_metric_details_reprojects_geographic() -> None:
    """A 0.1 degree WGS84 tile near Delhi becomes a real UTM 43N grid."""
    details = SpatialDetails(
        crs="EPSG:4326",
        # GDAL order: x0=77.0, pixel width 1e-4 deg, y0=28.0, pixel height -1e-4 deg.
        transform=AffineTransform(a=77.0, b=0.0001, c=0.0, d=28.0, e=0.0, f=-0.0001),
        bounds=Bounds(min_x=77.0, min_y=27.9, max_x=77.1, max_y=28.0),
        raster_width=1000,
        raster_height=1000,
    )
    result = projected_metric_details(details)
    assert result.crs == "EPSG:32643"
    assert result.units == "meters"
    assert result.transform is not None and result.bounds is not None
    # ~1e-4 deg is ~10 m on the ground; real UTM eastings carry the 500 km
    # false easting (77E is ~2 deg east of the 75E central meridian).
    assert 8.0 < result.transform.b < 12.0
    assert 680_000 < result.bounds.min_x < 720_000
    assert 3_080_000 < result.bounds.min_y < 3_110_000
