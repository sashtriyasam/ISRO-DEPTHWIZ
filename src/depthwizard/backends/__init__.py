"""Depth model backends — synthetic fixture and real model adapters."""

from depthwizard.backends.depth_anything_v2 import DepthAnythingV2Backend
from depthwizard.backends.depth_anything_v2_large import DepthAnythingV2LargeBackend
from depthwizard.backends.m17 import BACKEND_ID as M17_BACKEND_ID
from depthwizard.backends.m17 import M17DepthBackend
from depthwizard.backends.satellite import BACKEND_ID as SATELLITE_BACKEND_ID
from depthwizard.backends.satellite import SatelliteDepthBackend
from depthwizard.backends.synthetic import (
    MODEL_NAME,
    MODEL_VERSION,
    SyntheticDepthBackend,
    synthetic_depth_values,
)

__all__ = [
    "MODEL_NAME",
    "MODEL_VERSION",
    "DepthAnythingV2Backend",
    "DepthAnythingV2LargeBackend",
    "M17_BACKEND_ID",
    "M17DepthBackend",
    "SATELLITE_BACKEND_ID",
    "SatelliteDepthBackend",
    "SyntheticDepthBackend",
    "synthetic_depth_values",
]
