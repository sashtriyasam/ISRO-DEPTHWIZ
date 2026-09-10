"""Segment Anything Model depth refinement adapter (protocols + stubs).

Provides ``SAMRefiner`` protocol, ``EdgeAwareBilateralRefiner`` (numpy-only),
and ``BuildingRANSACRefiner`` stub (requires scipy).
"""

from __future__ import annotations

from typing import Protocol

import numpy as np


class SAMRefiner(Protocol):
    """Depth refinement boundary using semantic guidance."""

    def refine_depth(
        self,
        rgb: np.ndarray,
        depth: np.ndarray,
        semantic_mask: np.ndarray | None = None,
    ) -> np.ndarray:
        """Return a refined depth map matching the input resolution.

        Parameters
        ----------
        rgb:
            HxWx3 uint8 RGB image.
        depth:
            HxW float32/float64 depth map (scale-ambiguous or metric).
        semantic_mask:
            Optional HxW int16 ``LandCoverClass`` map.

        Returns
        -------
        np.ndarray
            Refined HxW depth map.
        """
        ...


class EdgeAwareBilateralRefiner:
    """Numpy-only bilateral filter for depth refinement.

    Smooths depth within homogeneous regions while preserving edges
    guided by RGB luminance.
    """

    def __init__(
        self,
        spatial_sigma: float = 2.0,
        range_sigma: float = 0.1,
        iterations: int = 1,
    ) -> None:
        self.spatial_sigma = spatial_sigma
        self.range_sigma = range_sigma
        self.iterations = iterations

    def refine_depth(
        self,
        rgb: np.ndarray,
        depth: np.ndarray,
        semantic_mask: np.ndarray | None = None,
    ) -> np.ndarray:
        if not isinstance(depth, np.ndarray) or depth.ndim != 2:
            raise ValueError("depth must be a 2D NumPy array")
        if depth.size == 0:
            return depth.copy()

        h, w = depth.shape
        out: np.ndarray = depth.astype(np.float64, copy=True)
        radius = max(1, int((2.0 * self.spatial_sigma) + 0.5))

        y, x = np.ogrid[-radius : radius + 1, -radius : radius + 1]
        spatial_weights = np.exp(-(x * x + y * y) / (2.0 * self.spatial_sigma * self.spatial_sigma))

        for _ in range(self.iterations):
            padded_depth = np.pad(out, radius, mode="edge")
            if rgb is not None and rgb.ndim == 3 and rgb.shape[:2] == (h, w):
                lum = (
                    0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
                ) / 255.0
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
                        radius + dy : radius + dy + h,
                        radius + dx : radius + dx + w,
                    ]
                    slice_guide = padded_guide[
                        radius + dy : radius + dy + h,
                        radius + dx : radius + dx + w,
                    ]
                    diff = slice_guide - padded_guide[radius : radius + h, radius : radius + w]
                    w_r = np.exp(-(diff * diff) / (2.0 * self.range_sigma * self.range_sigma))
                    weight = w_s * w_r
                    accum_val += weight * slice_depth
                    accum_weight += weight

            mask = accum_weight > 0
            out[mask] = accum_val[mask] / accum_weight[mask]

        return out.astype(depth.dtype)


class BuildingRANSACRefiner:
    """Stub for building-plane RANSAC depth refinement (requires scipy)."""

    def refine_depth(
        self,
        rgb: np.ndarray,
        depth: np.ndarray,
        semantic_mask: np.ndarray | None = None,
    ) -> np.ndarray:
        raise ImportError(
            "BuildingRANSACRefiner requires scipy; install depthwizard[research] to enable."
        )
