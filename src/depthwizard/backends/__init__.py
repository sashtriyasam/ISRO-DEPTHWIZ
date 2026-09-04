"""Depth model backends — synthetic fixture and real model adapters."""

from depthwizard.backends.depth_anything_v2 import DepthAnythingV2Backend
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
    "SyntheticDepthBackend",
    "synthetic_depth_values",
]
