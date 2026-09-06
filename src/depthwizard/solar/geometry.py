"""Shadow-height trigonometry with explicit direction validation.

Pixel-frame convention (documented, fixed): columns increase to the
right, rows increase downward.  A shadow direction angle is measured
with ``atan2(d_row, d_col)`` in that frame, in degrees on ``(-180, 180]``.

Direction validation compares the observed shadow direction against an
analyst-provided expected direction (which encodes the image's
orientation knowledge).  Without an expected direction the observation
is carried as direction-unvalidated — never auto-derived from solar
azimuth, because that mapping needs orientation metadata this module
refuses to invent.
"""

from __future__ import annotations

import math

from depthwizard.errors import InvalidInputError
from depthwizard.solar.models import ShadowHeightConstraint, ShadowObservation


def shadow_direction_deg(observation: ShadowObservation) -> float:
    """Observed shadow direction in pixel-frame degrees on (-180, 180]."""
    d_row = observation.tip.row - observation.base.row
    d_col = observation.tip.col - observation.base.col
    return math.degrees(math.atan2(d_row, d_col))


def _angular_difference_deg(first: float, second: float) -> float:
    """Smallest absolute angular difference in degrees [0, 180]."""
    return abs((first - second + 180.0) % 360.0 - 180.0)


def estimate_height(observation: ShadowObservation) -> ShadowHeightConstraint:
    """Derive an independent height cue from one shadow observation.

    Applies ``height = length_px × GSD × tan(elevation)``.  When the
    observation carries an expected shadow direction, agreement is
    validated against the tolerance and contradictions are refused.
    Occluded/ambiguous observations must never reach this function —
    the analyst quality flag travels through untouched for downstream
    filtering.
    """
    if not isinstance(observation, ShadowObservation):
        raise InvalidInputError(
            f"estimate_height requires a ShadowObservation, got {type(observation).__name__}"
        )

    observed = shadow_direction_deg(observation)
    agreement: float | None = None
    if observation.expected_shadow_angle_deg is not None:
        agreement = _angular_difference_deg(observed, observation.expected_shadow_angle_deg)
        if agreement > observation.angle_tolerance_deg:
            raise InvalidInputError(
                f"shadow direction {observed:.2f}° disagrees with expected "
                f"{observation.expected_shadow_angle_deg:.2f}° by {agreement:.2f}° "
                f"(tolerance {observation.angle_tolerance_deg:.2f}°): "
                "ambiguous association refused"
            )

    height = (
        observation.shadow_length_px
        * observation.gsd_m_per_px
        * math.tan(math.radians(observation.sun_elevation_deg))
    )
    if not math.isfinite(height) or height <= 0.0:
        raise InvalidInputError(
            "shadow geometry produced a non-positive height: check length, GSD and solar elevation"
        )

    assumptions: tuple[str, ...] = (
        "flat local ground at structure foot",
        "unambiguous shadow-to-structure association",
        f"explicit sun elevation {observation.sun_elevation_deg}° "
        f"and azimuth {observation.sun_azimuth_deg}° (provided, never inferred)",
        f"explicit GSD {observation.gsd_m_per_px} m/px",
    )
    if observation.expected_shadow_angle_deg is None:
        assumptions = assumptions + ("shadow direction unvalidated (no orientation knowledge)",)

    return ShadowHeightConstraint(
        height_m=height,
        units="meters",
        assumptions=assumptions,
        direction_agreement_deg=agreement,
        source_input_id=observation.source_input_id,
        source_checksum=observation.source_checksum,
        method=observation.method,
        quality=observation.quality,
    )
