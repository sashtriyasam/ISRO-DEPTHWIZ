"""Local UTM projection helper for geographic CRS rasters.

Provides structured resolution of local UTM EPSG codes and metric
coordinate conversions without silent transformations.
"""

from __future__ import annotations

import math

from depthwizard.contracts.spatial import Bounds, SpatialDetails


def resolve_local_utm_crs(lon: float, lat: float) -> str:
    """Determine the EPSG string for the local UTM zone at a given (lon, lat).

    Parameters
    ----------
    lon:
        Longitude in degrees [-180, 180].
    lat:
        Latitude in degrees [-80, 84].

    Returns
    -------
    str
        EPSG code string, e.g. ``"EPSG:32643"`` for Northern Hemisphere zone 43.
    """
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"longitude out of range [-180, 180]: {lon}")
    if not (-80.0 <= lat <= 84.0):
        raise ValueError(f"latitude out of WGS84 UTM bounds [-80, 84]: {lat}")

    zone = int(math.floor((lon + 180.0) / 6.0)) + 1
    if zone > 60:
        zone = 60

    is_northern = lat >= 0
    epsg_code = (32600 + zone) if is_northern else (32700 + zone)
    return f"EPSG:{epsg_code}"


def projected_metric_details(details: SpatialDetails) -> SpatialDetails:
    """Describe the grid a geographic raster would occupy in its local UTM zone.

    Projected metric CRSs are returned unchanged. Geographic CRSs are
    reprojected with GDAL (``rasterio.warp.calculate_default_transform``):
    a real projection of the raster footprint, not degrees multiplied by an
    approximate metres-per-degree factor relabelled as UTM (which produced
    coordinates with no false easting and a fabricated CRS claim).

    The returned details describe a *target* grid; no pixels are resampled
    here (use ``geospatial.warp`` for that). Requires the raster size, from
    ``raster_width``/``raster_height`` or the bounds and pixel size.
    """
    from rasterio.crs import CRS
    from rasterio.warp import calculate_default_transform

    from depthwizard.geospatial.crs import crs_is_projected_metric
    from depthwizard.geospatial.transforms import from_affine

    if details.crs is None or details.transform is None or details.bounds is None:
        return details
    if crs_is_projected_metric(details.crs):
        return details
    source = CRS.from_string(details.crs)
    if not source.is_geographic:
        raise ValueError(f"cannot derive a local UTM grid from non-geographic CRS {details.crs!r}")

    bounds = details.bounds
    t = details.transform  # GDAL order: a=x0, b=pixel width, f=pixel height
    width = details.raster_width or max(1, round((bounds.max_x - bounds.min_x) / abs(t.b)))
    height = details.raster_height or max(1, round((bounds.max_y - bounds.min_y) / abs(t.f)))
    center_x = (bounds.min_x + bounds.max_x) / 2.0
    center_y = (bounds.min_y + bounds.max_y) / 2.0
    target_crs = resolve_local_utm_crs(center_x, center_y)

    affine, out_width, out_height = calculate_default_transform(
        source,
        CRS.from_string(target_crs),
        width,
        height,
        left=bounds.min_x,
        bottom=bounds.min_y,
        right=bounds.max_x,
        top=bounds.max_y,
    )
    transform = from_affine(affine)
    min_x = transform.a
    max_y = transform.d
    max_x = min_x + transform.b * out_width
    min_y = max_y + transform.f * out_height
    return SpatialDetails(
        crs=target_crs,
        transform=transform,
        bounds=Bounds(
            min_x=min(min_x, max_x),
            min_y=min(min_y, max_y),
            max_x=max(min_x, max_x),
            max_y=max(min_y, max_y),
        ),
        resolution_gsd=abs(transform.b)
        if abs(abs(transform.b) - abs(transform.f)) < 1e-9
        else None,
        units="meters",
        raster_width=out_width,
        raster_height=out_height,
        nodata=details.nodata,
        source="local-utm-reprojection",
    )
