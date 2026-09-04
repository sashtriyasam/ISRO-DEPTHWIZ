"""CRS parsing, validation and semantic comparison (rasterio/GDAL-backed).

No CRS class is invented here: ``rasterio.crs.CRS`` (GDAL/OSR, PROJ
included) is the structured representation. String comparison is never
used for equality — equivalent representations (EPSG code vs WKT vs
proj-string of the same system) compare equal when the library says so.
"""

from __future__ import annotations

from typing import Any

from depthwizard.contracts.spatial import SpatialContext, SpatialKind
from depthwizard.errors import GeospatialProcessingError, MissingCRSError


def parse_crs(crs_id: str) -> Any:
    """Parse a CRS identifier into its structured form (Any: untyped lib).

    Raises :class:`GeospatialProcessingError` for unparseable input
    (never returns a fake default).
    """
    from rasterio.crs import CRS

    try:
        return CRS.from_string(crs_id)
    except Exception as exc:
        raise GeospatialProcessingError(f"invalid CRS identifier {crs_id!r}: {exc}") from exc


def crs_equal(first: str, second: str) -> bool:
    """Structured CRS equality (equivalent representations compare equal)."""
    return bool(parse_crs(first) == parse_crs(second))


def require_crs(context: SpatialContext, operation: str) -> str:
    """Return the CRS id a CRS-requiring operation needs, or fail clearly.

    Non-georeferenced rasters remain valid inputs generally; only the
    operation at hand is refused, via :class:`MissingCRSError`.
    """
    details = context.details if context.kind is SpatialKind.PRESENT else None
    if details is None or details.crs is None:
        raise MissingCRSError(
            f"{operation} requires a CRS, but none is available "
            f"(spatial kind: {context.kind.value})"
        )
    return details.crs
