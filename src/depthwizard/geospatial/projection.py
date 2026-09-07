"""Local UTM projection helper for geographic CRS rasters.

Provides structured resolution of local UTM EPSG codes and metric
coordinate conversions without silent transformations.
"""

from __future__ import annotations

import math

from depthwizard.contracts.spatial import AffineTransform, SpatialDetails


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
    """Construct an explicit projected SpatialDetails if input CRS is geographic.

    If CRS is already projected (metres), returns details unchanged.
    If CRS is geographic (degrees), determines local UTM zone and estimates
    approximate metre scale factors for pixel resolution (1 deg lat ~ 111,320 m).

    Parameters
    ----------
    details:
        Source SpatialDetails.

    Returns
    -------
    SpatialDetails
        Updated SpatialDetails with projected metric CRS and transform.
    """
    if details.crs is None or details.transform is None or details.bounds is None:
        return details

    crs_str = str(details.crs).upper()
    if crs_str in ("EPSG:4326", "WGS84", "WGS 84", "OGC:CRS84", "EPSG:4269") or "GEOGCS" in crs_str:
        # Needs projection to local UTM
        pass
    elif "326" in crs_str or "327" in crs_str or "UTM" in crs_str or "PROJECTED" in crs_str:
        # Already projected
        return details

    center_x = (details.bounds.min_x + details.bounds.max_x) / 2.0
    center_y = (details.bounds.min_y + details.bounds.max_y) / 2.0

    target_crs = resolve_local_utm_crs(center_x, center_y)

    # 1 deg lat = ~111,320 m; 1 deg lon = ~111,320 * cos(lat) m
    lat_rad = math.radians(center_y)
    m_per_deg_lat = 111_320.0
    m_per_deg_lon = 111_320.0 * math.cos(lat_rad)

    t = details.transform
    proj_a = t.a * m_per_deg_lon
    proj_e = t.e * m_per_deg_lat
    proj_c = t.c * m_per_deg_lon
    proj_f = t.f * m_per_deg_lat

    proj_transform = AffineTransform(a=proj_a, b=t.b, c=proj_c, d=t.d, e=proj_e, f=proj_f)

    b = details.bounds
    proj_bounds = b.__class__(
        min_x=b.min_x * m_per_deg_lon,
        min_y=b.min_y * m_per_deg_lat,
        max_x=b.max_x * m_per_deg_lon,
        max_y=b.max_y * m_per_deg_lat,
    )

    return SpatialDetails(
        crs=target_crs,
        transform=proj_transform,
        bounds=proj_bounds,
    )
