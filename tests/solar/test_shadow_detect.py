"""Tests for deterministic Otsu luminance shadow detection."""

from __future__ import annotations

import numpy as np
import pytest

from depthwizard.solar.shadow_detect import ShadowRegion, detect_shadows


def _make_synthetic_shadow_image() -> np.ndarray:
    """Create a 100x100 RGB image with a bright background and a dark shadow rectangle."""
    # Bright illuminated background (e.g. 200, 200, 200)
    img = np.full((100, 100, 3), 200, dtype=np.uint8)
    # Dark shadow patch at rows [30:60], cols [40:70] (value 30)
    img[30:60, 40:70, :] = 30
    return img


def test_detect_shadows_finds_dark_region() -> None:
    """A clear dark rectangle on bright ground is detected as a shadow region."""
    img = _make_synthetic_shadow_image()
    regions = detect_shadows(img, min_area_px=20)
    assert len(regions) == 1
    region = regions[0]
    assert isinstance(region, ShadowRegion)
    assert region.area_px == 30 * 30  # 900 px
    assert region.bbox.row_min == 30
    assert region.bbox.row_max == 59
    assert region.bbox.col_min == 40
    assert region.bbox.col_max == 69
    assert 30 <= region.centroid_row <= 60
    assert 40 <= region.centroid_col <= 70
    assert region.quality in ("clear", "occluded", "uncertain")


def test_detect_shadows_min_area_filter() -> None:
    """Regions smaller than min_area_px are filtered out."""
    img = _make_synthetic_shadow_image()
    # If min_area is larger than 900 px, region is rejected
    regions = detect_shadows(img, min_area_px=1000)
    assert len(regions) == 0


def test_detect_shadows_uniform_image() -> None:
    """Uniform images produce zero shadow regions (no bimodal contrast)."""
    img = np.full((50, 50, 3), 150, dtype=np.uint8)
    regions = detect_shadows(img, min_area_px=20)
    assert len(regions) == 0


def test_detect_shadows_invalid_inputs() -> None:
    """Invalid input types and shapes raise ValueError/TypeError."""
    with pytest.raises(TypeError):
        detect_shadows("not an array")  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        detect_shadows(np.zeros((50, 50), dtype=np.uint8))  # 2D

    with pytest.raises(ValueError):
        detect_shadows(np.zeros((50, 50, 3), dtype=np.uint8), min_area_px=0)
