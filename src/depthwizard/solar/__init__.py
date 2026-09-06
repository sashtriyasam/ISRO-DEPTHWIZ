"""Solar-shadow geometry: explicit observations, honest heights."""

from depthwizard.solar.geometry import estimate_height, shadow_direction_deg
from depthwizard.solar.models import (
    PixelPoint,
    ShadowHeightConstraint,
    ShadowObservation,
)

__all__ = [
    "PixelPoint",
    "ShadowHeightConstraint",
    "ShadowObservation",
    "estimate_height",
    "shadow_direction_deg",
]
