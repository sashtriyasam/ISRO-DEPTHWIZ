"""Depth model backends (synthetic fixture today, real adapters later)."""

from depthwizard.backends.synthetic import (
    MODEL_NAME,
    MODEL_VERSION,
    SyntheticDepthBackend,
    synthetic_depth_values,
)

__all__ = [
    "MODEL_NAME",
    "MODEL_VERSION",
    "SyntheticDepthBackend",
    "synthetic_depth_values",
]
