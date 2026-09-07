"""Solar-shadow geometry: explicit observations, honest heights."""

from depthwizard.solar.geometry import estimate_height, shadow_direction_deg
from depthwizard.solar.integrate import (
    SolarIntegrationResult,
    load_image_rgb,
    solar_observations_from_image,
)
from depthwizard.solar.models import (
    PixelPoint,
    ShadowHeightConstraint,
    ShadowObservation,
)
from depthwizard.solar.shadow_detect import ShadowRegion, detect_shadows, gsd_from_inspection
from depthwizard.solar.sun_angles import SunAngles, resolve_sun_angles

__all__ = [
    # core trig
    "PixelPoint",
    "ShadowHeightConstraint",
    "ShadowObservation",
    "estimate_height",
    "shadow_direction_deg",
    # sun-angle resolver
    "SunAngles",
    "resolve_sun_angles",
    # shadow detector
    "ShadowRegion",
    "detect_shadows",
    "gsd_from_inspection",
    # integration
    "SolarIntegrationResult",
    "load_image_rgb",
    "solar_observations_from_image",
]
