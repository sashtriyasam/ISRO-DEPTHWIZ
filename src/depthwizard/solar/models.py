"""Solar-shadow geometry: explicit shadow observations, honest heights.

A shadow observation records everything needed for the classical
single-image height relation ``height = length × GSD × tan(elevation)``
and nothing else.  Sun angles and ground sampling are REQUIRED inputs:
where they are unavailable the constructors refuse — this module never
invents sun position, date/time, location, or scale.  Results are
independent height cues with recorded assumptions, never automatic
ground truth and never a calibration replacement.
"""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.contracts.artifacts import METRIC_UNIT

#: Solar elevation must lie strictly inside (0, 90) degrees: at 0 the
#: sun is on the horizon (infinite height), at 90 there is no shadow.
MIN_ELEVATION_DEG = 0.0
MAX_ELEVATION_DEG = 90.0


class PixelPoint(BaseModel):
    """Integer pixel coordinates (row, col) in the source image grid."""

    model_config = ConfigDict(frozen=True)

    row: int = Field(ge=0)
    col: int = Field(ge=0)


class ShadowObservation(BaseModel):
    """One validated building-shadow observation in pixel space.

    The shadow runs from ``base`` (structure foot) to ``tip`` (shadow
    end).  Length is explicit (not recomputed from endpoints) so the
    recorded value always matches the analyst's measurement; endpoints
    additionally must be distinct points.
    """

    model_config = ConfigDict(frozen=True)

    source_input_id: str = Field(min_length=1)
    source_checksum: str | None = None
    base: PixelPoint
    tip: PixelPoint
    shadow_length_px: float = Field(gt=0.0)
    gsd_m_per_px: float = Field(gt=0.0, description="Explicit ground sampling distance.")
    sun_elevation_deg: float = Field(description="Solar elevation, strictly inside (0, 90).")
    sun_azimuth_deg: float = Field(
        description="Solar azimuth in degrees [0, 360): direction TO the sun."
    )
    expected_shadow_angle_deg: float | None = Field(
        default=None,
        description="Expected shadow direction in pixel-frame degrees, if the "
        "image orientation is known. Absent means direction is unvalidated.",
    )
    angle_tolerance_deg: float = Field(
        default=10.0,
        gt=0.0,
        le=45.0,
        description="Agreement tolerance when expected direction is set.",
    )
    method: str = Field(min_length=1, description="How the shadow was segmented.")
    quality: str = Field(
        default="unvalidated",
        description="Analyst quality flag, e.g. 'unvalidated', 'clear', 'occluded'.",
    )

    @model_validator(mode="after")
    def _check_observation_honesty(self) -> ShadowObservation:
        if not math.isfinite(self.shadow_length_px):
            raise ValueError("shadow_length_px must be finite")
        if not math.isfinite(self.gsd_m_per_px):
            raise ValueError("gsd_m_per_px must be finite")
        if not math.isfinite(self.sun_elevation_deg) or not (
            MIN_ELEVATION_DEG < self.sun_elevation_deg < MAX_ELEVATION_DEG
        ):
            raise ValueError("sun_elevation_deg must lie strictly inside (0, 90)")
        if not math.isfinite(self.sun_azimuth_deg) or not (0.0 <= self.sun_azimuth_deg < 360.0):
            raise ValueError("sun_azimuth_deg must lie in [0, 360)")
        if self.base == self.tip:
            raise ValueError("base and tip must be distinct pixels")
        if self.expected_shadow_angle_deg is not None and not math.isfinite(
            self.expected_shadow_angle_deg
        ):
            raise ValueError("expected_shadow_angle_deg must be finite when provided")
        return self


class ShadowHeightConstraint(BaseModel):
    """Height cue derived from exactly one shadow observation.

    An independent constraint for validation — never automatic ground
    truth, never a calibration replacement.
    """

    model_config = ConfigDict(frozen=True)

    height_m: float = Field(gt=0.0, description="Estimated structure height in metres.")
    units: str = Field(description="Always explicit metric units ('meters').")
    assumptions: tuple[str, ...] = Field(
        description="Recorded assumptions, e.g. flat ground, unambiguous association."
    )
    direction_agreement_deg: float | None = Field(
        default=None,
        description="Angular difference between observed and expected shadow "
        "direction, when direction was validated.",
    )
    source_input_id: str = Field(min_length=1)
    source_checksum: str | None = None
    method: str = Field(min_length=1)
    quality: str = Field(default="unvalidated")

    @model_validator(mode="after")
    def _check_constraint_honesty(self) -> ShadowHeightConstraint:
        if not math.isfinite(self.height_m):
            raise ValueError("height_m must be finite")
        if self.units != METRIC_UNIT:
            raise ValueError(f"shadow height units must be ('{METRIC_UNIT}')")
        if not self.assumptions:
            raise ValueError("assumptions must record at least the flat-ground assumption")
        if self.direction_agreement_deg is not None and not math.isfinite(
            self.direction_agreement_deg
        ):
            raise ValueError("direction_agreement_deg must be finite when recorded")
        return self
