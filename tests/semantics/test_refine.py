"""Tests for depth map bilateral refinement."""

from __future__ import annotations

import numpy as np
import pytest

from depthwizard.semantics.refine import refine_depth_map


def test_refine_depth_map_preserves_shape() -> None:
    """Refinement preserves original array shape and dtype."""
    depth = np.random.rand(50, 50).astype(np.float32)
    refined = refine_depth_map(depth)
    assert refined.shape == (50, 50)
    assert refined.dtype == np.float32


def test_refine_depth_map_smooths_flat_region() -> None:
    """Noisy flat region has variance reduced after bilateral filtering."""
    np.random.seed(42)
    flat = np.full((30, 30), 10.0, dtype=np.float64)
    noisy = flat + np.random.normal(0, 0.5, (30, 30))

    refined = refine_depth_map(noisy, spatial_sigma=2.0, range_sigma=1.0)
    assert np.var(refined) < np.var(noisy)


def test_refine_depth_map_preserves_sharp_edge() -> None:
    """Step edge between two flat regions is preserved (not blurred across boundary)."""
    step = np.zeros((40, 40), dtype=np.float64)
    step[:, 20:] = 50.0  # sharp step edge at col 20

    refined = refine_depth_map(step, spatial_sigma=1.5, range_sigma=0.5)
    # Check that left region stays near 0 and right region stays near 50
    assert np.abs(refined[20, 5] - 0.0) < 0.1
    assert np.abs(refined[20, 35] - 50.0) < 0.1


def test_refine_depth_map_with_rgb_guide() -> None:
    """Joint bilateral filtering using an RGB image guide."""
    depth = np.full((20, 20), 5.0, dtype=np.float32)
    rgb = np.full((20, 20, 3), 128, dtype=np.uint8)

    refined = refine_depth_map(depth, rgb=rgb)
    assert refined.shape == (20, 20)
    assert np.allclose(refined, 5.0, atol=1e-3)


def test_refine_depth_map_invalid_inputs() -> None:
    """Invalid input shapes/types raise ValueError."""
    with pytest.raises(ValueError):
        refine_depth_map(np.zeros((10, 10, 10)))  # 3D

    with pytest.raises(ValueError):
        refine_depth_map(np.zeros((10, 10)), rgb=np.zeros((10, 15, 3), dtype=np.uint8))
