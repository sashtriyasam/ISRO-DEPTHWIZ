"""Semantic land-cover classification (rule-based, numpy-only).

Provides LandCoverClass constants, a TerrainClassifier protocol,
and RuleBasedTerrainClassifier using simple RGB heuristics.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Protocol

import numpy as np
from pydantic import BaseModel, ConfigDict, Field


class LandCoverClass(IntEnum):
    """Integer land-cover class identifiers for semantic masks."""

    UNKNOWN = 0
    BUILDING = 1
    ROAD = 2
    BARE_SOIL = 3
    VEGETATION = 4
    WATER = 5
    SHADOW = 6


class TerrainClassifier(Protocol):
    """Surface-type classification boundary."""

    def classify(self, rgb: np.ndarray) -> np.ndarray:
        """Return a 2D integer class map matching the input resolution."""
        ...


class RuleBasedTerrainClassifier:
    """Deterministic rule-based land-cover classifier (no learned model)."""

    def __init__(
        self,
        luminance_threshold: float = 30.0,
        green_dominance_threshold: float = 1.05,
        blue_dominance_threshold: float = 1.2,
        saturation_threshold: float = 40.0,
        edge_threshold: float = 0.15,
        texture_variance_threshold: float = 100.0,
        bare_soil_green_threshold: float = 80.0,
        bare_soil_blue_threshold: float = 100.0,
    ) -> None:
        self.luminance_threshold = luminance_threshold
        self.green_dominance_threshold = green_dominance_threshold
        self.blue_dominance_threshold = blue_dominance_threshold
        self.saturation_threshold = saturation_threshold
        self.edge_threshold = edge_threshold
        self.texture_variance_threshold = texture_variance_threshold
        self.bare_soil_green_threshold = bare_soil_green_threshold
        self.bare_soil_blue_threshold = bare_soil_blue_threshold

    def classify(self, rgb: np.ndarray) -> np.ndarray:
        if rgb.ndim != 3 or rgb.shape[2] != 3:
            raise ValueError("rgb must be HxWx3")
        h, w = rgb.shape[:2]
        r = rgb[:, :, 0].astype(np.float64)
        g = rgb[:, :, 1].astype(np.float64)
        b = rgb[:, :, 2].astype(np.float64)

        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        max_c = np.maximum(np.maximum(r, g), b)
        min_c = np.minimum(np.minimum(r, g), b)
        saturation = np.where(max_c > 0, (max_c - min_c) / max_c * 255.0, 0.0)

        class_map = np.full((h, w), LandCoverClass.UNKNOWN, dtype=np.int16)

        water = (saturation < self.saturation_threshold) & (
            (b > self.blue_dominance_threshold * r) & (b > self.blue_dominance_threshold * g)
        )
        class_map[water] = LandCoverClass.WATER

        vegetation = (g > self.green_dominance_threshold * r) & ~water
        class_map[vegetation] = LandCoverClass.VEGETATION

        shadow = (lum < self.luminance_threshold) & ~water & ~vegetation
        class_map[shadow] = LandCoverClass.SHADOW

        gray = lum.astype(np.float32)
        dx = _sobel_horizontal(gray)
        dy = _sobel_vertical(gray)
        edge_mag = np.hypot(dx, dy)
        edge_strength = _local_mean(edge_mag, 3)
        building = (edge_strength > self.edge_threshold) & ~water & ~vegetation & ~shadow
        class_map[building] = LandCoverClass.BUILDING

        tex_var = _local_variance(gray, 5)
        road = (
            (tex_var < self.texture_variance_threshold) & ~water & ~vegetation & ~shadow & ~building
        )
        class_map[road] = LandCoverClass.ROAD

        bare = (
            (g < self.bare_soil_green_threshold)
            & (b < self.bare_soil_blue_threshold)
            & ~water
            & ~vegetation
            & ~shadow
            & ~building
            & ~road
        )
        class_map[bare] = LandCoverClass.BARE_SOIL

        return class_map


def _sobel_horizontal(gray: np.ndarray) -> np.ndarray:
    padded = np.pad(gray, 1, mode="edge")
    return (
        -padded[:-2, :-2]
        - 2.0 * padded[:-2, 1:-1]
        - padded[:-2, 2:]
        + padded[2:, :-2]
        + 2.0 * padded[2:, 1:-1]
        + padded[2:, 2:]
    ) / 8.0


def _sobel_vertical(gray: np.ndarray) -> np.ndarray:
    padded = np.pad(gray, 1, mode="edge")
    return (
        -padded[:-2, :-2]
        - 2.0 * padded[1:-1, :-2]
        - padded[2:, :-2]
        + padded[:-2, 2:]
        + 2.0 * padded[1:-1, 2:]
        + padded[2:, 2:]
    ) / 8.0


def _conv2d(arr: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    kh, kw = kernel.shape
    pad_h, pad_w = kh // 2, kw // 2
    padded = np.pad(arr, ((pad_h, pad_h), (pad_w, pad_w)), mode="edge")
    out = np.zeros_like(arr, dtype=np.float64)
    for dy in range(kh):
        for dx in range(kw):
            out += kernel[dy, dx] * padded[dy : dy + arr.shape[0], dx : dx + arr.shape[1]]
    return out


def _local_mean(arr: np.ndarray, k: int) -> np.ndarray:
    kernel = np.ones((k, k), dtype=np.float64) / (k * k)
    return _conv2d(arr, kernel)


def _local_variance(arr: np.ndarray, k: int) -> np.ndarray:
    mean = _local_mean(arr, k)
    mean_sq = _local_mean(arr * arr, k)
    return np.maximum(mean_sq - mean * mean, 0.0)


class SemanticMask(BaseModel):
    """Semantic classification result for one image."""

    model_config = ConfigDict(frozen=True)

    class_map: np.ndarray = Field(description="HxW int16 array of LandCoverClass values.")
    class_probabilities: tuple[tuple[float, ...], ...] | None = Field(
        default=None,
        description="Per-class confidence per pixel.",
    )
    class_names: tuple[str, ...] = Field(
        default=("UNKNOWN", "BUILDING", "ROAD", "BARE_SOIL", "VEGETATION", "WATER", "SHADOW"),
        description="Class names ordered by LandCoverClass value.",
    )
    method: str = Field(min_length=1, description="Classifier method identifier.")
