"""Spatial metadata contract (descriptive only, no CRS math).

Carries CRS identifiers, affine transforms, bounds and raster shape
without implementing reprojection, alignment or resampling. Those
belong to later geospatial tasks (Rasterio / GDAL / pyproj).

Unknown values stay ``None`` — never fake defaults. Whether spatial
information is present at all is explicit via :class:`SpatialKind`.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SpatialKind(str, Enum):
    """Whether spatial metadata is present, unavailable, or not applicable."""

    PRESENT = "present"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


class AffineTransform(BaseModel):
    """Six-parameter GDAL-style affine transform (a, b, c, d, e, f).

    x_geo = a + b * col + c * row
    y_geo = d + e * col + f * row
    """

    model_config = ConfigDict(frozen=True)

    a: float
    b: float
    c: float
    d: float
    e: float
    f: float

    def as_tuple(self) -> tuple[float, float, float, float, float, float]:
        """Return the six parameters in GDAL order."""
        return (self.a, self.b, self.c, self.d, self.e, self.f)


class Bounds(BaseModel):
    """Axis-aligned bounding box in the product CRS (when known)."""

    model_config = ConfigDict(frozen=True)

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @model_validator(mode="after")
    def _check_order(self) -> Bounds:
        if self.max_x < self.min_x or self.max_y < self.min_y:
            raise ValueError("bounds max must be >= min on both axes")
        return self


class SpatialDetails(BaseModel):
    """Concrete spatial fields. Every field is optional: unknown stays None."""

    model_config = ConfigDict(frozen=True)

    crs: str | None = Field(
        default=None, description="CRS identifier, e.g. 'EPSG:4326'. None when unknown."
    )
    transform: AffineTransform | None = None
    bounds: Bounds | None = None
    pixel_width: int | None = Field(default=None, gt=0)
    pixel_height: int | None = Field(default=None, gt=0)
    resolution_gsd: float | None = Field(
        default=None, gt=0, description="Ground sampling distance in CRS units, if known."
    )
    nodata: float | None = Field(default=None, description="Nodata marker, if defined.")
    units: str | None = Field(
        default=None, description="Planimetric units, e.g. 'meters'. None when unknown."
    )
    raster_width: int | None = Field(default=None, gt=0)
    raster_height: int | None = Field(default=None, gt=0)
    source: str | None = Field(
        default=None, description="Where the spatial metadata came from, if known."
    )


class SpatialContext(BaseModel):
    """Explicit wrapper distinguishing present / unavailable / not applicable."""

    model_config = ConfigDict(frozen=True)

    kind: SpatialKind
    details: SpatialDetails | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> SpatialContext:
        if self.kind is SpatialKind.PRESENT:
            if self.details is None:
                raise ValueError("PRESENT spatial context requires details")
            if (
                self.details.crs is None
                and self.details.transform is None
                and self.details.bounds is None
            ):
                raise ValueError(
                    "PRESENT spatial context requires at least one of crs/transform/bounds"
                )
        elif self.details is not None:
            raise ValueError(f"{self.kind.value} spatial context must not carry details")
        return self
