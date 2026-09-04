"""Reference-control contracts (explicit, auditable, immutable).

``SurfaceElevationControl`` is caller-supplied ground truth about the
surface (never derived from models or DEMs). ``ReferenceControlPoint``
is the built, fully-resolved control: prediction, surface, optional
terrain context, and derived metric reference with source linkage.
Construction is fail-fast — every built control is valid, so batches
stay one-to-one without silent exclusion.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.contracts.semantics import ElevationSemantics


class CoordinateSpace(str, Enum):
    """Authoritative coordinate space of a surface control."""

    PIXEL = "pixel"
    WORLD = "world"


class SurfaceElevationControl(BaseModel):
    """Caller-supplied surface elevation with explicit coordinates.

    Exactly one space is authoritative (``coordinate_space``); the
    other pair may be supplied for cross-checking and is verified at
    build time. Legitimate future sources: surveyed rooftops,
    validated DSM/stereo controls, benchmark surface points.
    """

    model_config = ConfigDict(frozen=True)

    control_id: str = Field(min_length=1)
    coordinate_space: CoordinateSpace
    row: int | None = Field(default=None, ge=0)
    col: int | None = Field(default=None, ge=0)
    x: float | None = None
    y: float | None = None
    crs: str | None = Field(
        default=None,
        description="Frame of (x, y); None means the source depth frame.",
    )
    surface_elevation_m: float
    units: str = Field(description="Must be explicit 'meters'.")
    source_id: str = Field(min_length=1, description="Who/what supplied it.")
    source_checksum: str | None = None
    description: str | None = None

    @model_validator(mode="after")
    def _check_control(self) -> SurfaceElevationControl:
        import math

        if not math.isfinite(self.surface_elevation_m):
            raise ValueError("surface elevation must be finite")
        if self.units != "meters":
            raise ValueError("surface control units must be explicit 'meters'")
        for name in ("row", "col"):
            value = getattr(self, name)
            if value is not None and isinstance(value, bool):
                raise ValueError(f"{name} must be an integer index, not boolean")
        if self.coordinate_space is CoordinateSpace.PIXEL:
            if self.row is None or self.col is None:
                raise ValueError("pixel-space controls require row and col")
        else:
            if self.x is None or self.y is None:
                raise ValueError("world-space controls require x and y")
            if not math.isfinite(self.x) or not math.isfinite(self.y):
                raise ValueError("world coordinates must be finite")
        for pair, names in (
            ((self.row, self.col), ("row", "col")),
            ((self.x, self.y), ("x", "y")),
        ):
            if (pair[0] is None) != (pair[1] is None):
                raise ValueError(f"{names[0]} and {names[1]} must be given together")
        return self


class ReferenceControlPoint(BaseModel):
    """Resolved control: prediction + surface + optional terrain context.

    ``terrain_elevation_m`` is None for absolute-elevation controls
    built without a terrain grid, or when contextual sampling found no
    valid terrain. ``reference_value`` is the metric calibration
    reference (surface, or surface minus terrain for AGL).
    """

    model_config = ConfigDict(frozen=True)

    control_id: str = Field(min_length=1)
    target_semantics: ElevationSemantics
    units: str = "meters"
    row: int = Field(ge=0)
    col: int = Field(ge=0)
    x: float | None = None
    y: float | None = None
    pixel_col: float | None = None
    pixel_row: float | None = None
    predicted_value: float
    surface_elevation_m: float
    terrain_elevation_m: float | None = None
    reference_value: float
    surface_source_id: str
    surface_source_checksum: str | None = None
    terrain_source_id: str | None = None
    terrain_source_checksum: str | None = None
    depth_model: str = Field(min_length=1)
    depth_checksum: str | None = None
    depth_input_id: str | None = None

    @model_validator(mode="after")
    def _check_point(self) -> ReferenceControlPoint:
        import math

        if self.units != "meters":
            raise ValueError("reference controls use explicit metric units")
        if self.target_semantics not in (
            ElevationSemantics.HEIGHT_AGL_NDSM,
            ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        ):
            raise ValueError("reference controls target metric height meanings only")
        for name in ("predicted_value", "surface_elevation_m", "reference_value"):
            if not math.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite")
        if self.terrain_elevation_m is not None and not math.isfinite(self.terrain_elevation_m):
            raise ValueError("terrain elevation must be finite when present")
        return self
