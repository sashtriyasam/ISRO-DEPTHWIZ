"""Semantic and edge-preserving depth refinement algorithms.

Provides ``refine_depth_map()`` to smooth depth within homogeneous regions
while preserving sharp boundaries at building edges and terrain transitions.
"""

from __future__ import annotations

import math

import numpy as np


def refine_depth_map(
    depth: np.ndarray,
    rgb: np.ndarray | None = None,
    *,
    spatial_sigma: float = 2.0,
    range_sigma: float = 0.1,
    iterations: int = 1,
) -> np.ndarray:
    """Apply edge-aware bilateral filtering to a 2D float depth map.

    Smooths depth noise within continuous structures (e.g. rooftops)
    while preserving sharp step discontinuities at object edges.

    Parameters
    ----------
    depth:
        2D float32 or float64 NumPy array (height, width).
    rgb:
        Optional 3D HxWx3 uint8 RGB image for joint bilateral filtering.
        If None, range weights are computed directly from depth differences.
    spatial_sigma:
        Gaussian spatial kernel standard deviation (in pixels).
    range_sigma:
        Gaussian range kernel standard deviation (in depth / color units).
    iterations:
        Number of refinement passes (default 1).

    Returns
    -------
    np.ndarray
        Refined 2D float depth map with preserved edges.
    """
    if not isinstance(depth, np.ndarray) or depth.ndim != 2:
        raise ValueError("depth must be a 2D float NumPy array")
    if depth.size == 0:
        return depth.copy()

    h, w = depth.shape
    out: np.ndarray = depth.astype(np.float64, copy=True)
    radius = max(1, int(math.ceil(2.0 * spatial_sigma)))

    # Pre-calculate spatial Gaussian kernel
    y, x = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    spatial_weights = np.exp(-(x * x + y * y) / (2.0 * spatial_sigma * spatial_sigma))

    for _ in range(iterations):
        padded_depth = np.pad(out, radius, mode="edge")
        if rgb is not None:
            if rgb.ndim != 3 or rgb.shape[:2] != (h, w):
                raise ValueError("rgb must be HxWx3 matching depth shape")
            lum = (0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]) / 255.0
            padded_guide = np.pad(lum, radius, mode="edge")
        else:
            padded_guide = padded_depth

        accum_val = np.zeros((h, w), dtype=np.float64)
        accum_weight = np.zeros((h, w), dtype=np.float64)

        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                w_s = spatial_weights[dy + radius, dx + radius]
                if w_s < 1e-4:
                    continue
                slice_depth = padded_depth[
                    radius + dy : radius + dy + h, radius + dx : radius + dx + w
                ]
                slice_guide = padded_guide[
                    radius + dy : radius + dy + h, radius + dx : radius + dx + w
                ]

                diff = slice_guide - padded_guide[radius : radius + h, radius : radius + w]
                w_r = np.exp(-(diff * diff) / (2.0 * range_sigma * range_sigma))

                weight = w_s * w_r
                accum_val += weight * slice_depth
                accum_weight += weight

        mask = accum_weight > 0
        out[mask] = accum_val[mask] / accum_weight[mask]

    return out.astype(depth.dtype)
