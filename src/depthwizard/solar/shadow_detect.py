"""Deterministic shadow segmentation using luminance thresholding.

Segments shadow candidate regions from an RGB image using a purely
deterministic, reproducible algorithm with no ML dependency.  The method
is explicitly documented so every result can be reproduced from the same
inputs.

Algorithm
---------
1. Convert RGB to luminance: ``L = 0.2126·R + 0.7152·G + 0.0722·B``.
2. Compute an image histogram (256 bins, uint8).
3. Apply Otsu's threshold to find the dark/bright class boundary.
   Where the image has strong bimodal structure (shadows + illuminated
   surfaces) this finds the shadow fraction reliably.
4. Mark pixels below the threshold as candidate shadow.
5. Identify connected regions using a simple row-major scan with
   union-find (no scipy required).
6. Filter by minimum area; compute per-region bounding box, centroid,
   and the farthest dark pixel from the region's brightest edge pixel
   (used as the shadow tip approximation).

All outputs are pixel coordinates only.  No metric values are computed
here — metric shadow lengths require an explicit GSD that callers supply.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundingBox:
    """Pixel bounding box (inclusive on all sides)."""

    row_min: int
    row_max: int
    col_min: int
    col_max: int

    @property
    def height_px(self) -> int:
        return self.row_max - self.row_min + 1

    @property
    def width_px(self) -> int:
        return self.col_max - self.col_min + 1


@dataclass(frozen=True)
class ShadowRegion:
    """One detected candidate shadow region.

    Coordinates are 0-indexed pixel (row, col) in the source image grid.
    ``tip`` is the shadow-end pixel: the point farthest from the structure
    along the shadow direction.  When the image orientation is known, a
    direction consistency check is applied by ``integrate.py``.

    Quality flags:

    * ``clear``: region passes area filter; no obvious occlusion detected.
    * ``occluded``: region is large but has irregular or split shape.
    * ``uncertain``: region barely passes the area filter.
    """

    region_id: int
    bbox: BoundingBox
    centroid_row: float
    centroid_col: float
    area_px: int
    tip_row: int
    tip_col: int
    quality: str  # "clear" | "occluded" | "uncertain"
    method: str = "otsu-luminance-v1"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _luminance(rgb: np.ndarray) -> np.ndarray:
    """BT.709 luminance from HxWx3 uint8 array, returned as float32 HxW."""
    import numpy as np

    r: np.ndarray = rgb[:, :, 0].astype(np.float32)
    g: np.ndarray = rgb[:, :, 1].astype(np.float32)
    b: np.ndarray = rgb[:, :, 2].astype(np.float32)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b  # type: ignore[no-any-return]


def _otsu_threshold(lum: np.ndarray) -> float:
    """Otsu's method on a float luminance array (0–255 range).

    Returns the threshold value that minimises within-class variance.
    Uses a 256-bin histogram over the clamped [0, 255] range.
    """
    import numpy as np

    lum_u8 = np.clip(lum, 0, 255).astype(np.uint8)
    hist, _ = np.histogram(lum_u8, bins=256, range=(0, 256))
    hist = hist.astype(np.float64)
    total = float(lum_u8.size)
    if total == 0:
        return 127.0

    sum_total = float(np.dot(np.arange(256, dtype=np.float64), hist))
    sum_back = 0.0
    weight_back = 0.0
    best_variance = -1.0
    threshold = 127.0

    for t in range(256):
        weight_back += hist[t]
        if weight_back == 0:
            continue
        weight_fore = total - weight_back
        if weight_fore == 0:
            break
        sum_back += t * hist[t]
        mean_back = sum_back / weight_back
        mean_fore = (sum_total - sum_back) / weight_fore
        variance = weight_back * weight_fore * (mean_back - mean_fore) ** 2
        if variance > best_variance:
            best_variance = variance
            threshold = float(t)

    return threshold


def _connected_regions(
    mask: np.ndarray,
) -> np.ndarray:
    """Label connected components in a boolean mask (4-connectivity).

    Returns a label array of the same shape (dtype int32); background = 0.
    Uses a two-pass algorithm (row-major scan + union-find) with no
    scipy dependency.
    """
    import numpy as np

    h, w = mask.shape
    labels: np.ndarray = np.zeros((h, w), dtype=np.int32)
    parent: list[int] = [0]  # index 0 = background root

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    next_label = 1
    for row in range(h):
        for col in range(w):
            if not mask[row, col]:
                continue
            above = int(labels[row - 1, col]) if row > 0 else 0
            left = int(labels[row, col - 1]) if col > 0 else 0
            above_r = find(above) if above else 0
            left_r = find(left) if left else 0
            if above_r == 0 and left_r == 0:
                parent.append(next_label)
                labels[row, col] = next_label
                next_label += 1
            elif above_r != 0 and left_r == 0:
                labels[row, col] = above_r
            elif left_r != 0 and above_r == 0:
                labels[row, col] = left_r
            else:
                union(above_r, left_r)
                labels[row, col] = find(above_r)

    # Second pass: flatten labels
    for row in range(h):
        for col in range(w):
            if labels[row, col]:
                labels[row, col] = find(int(labels[row, col]))
    return labels


def _region_stats(
    labels: np.ndarray,
    shadow_rows: np.ndarray,
    shadow_cols: np.ndarray,
    region_label: int,
) -> tuple[BoundingBox, float, float, int, int, int]:
    """Compute bbox, centroid, area, and tip (farthest point from bbox top-left).

    Returns (bbox, centroid_row, centroid_col, area_px, tip_row, tip_col).
    """
    import numpy as np

    mask = labels[shadow_rows, shadow_cols] == region_label
    rows = shadow_rows[mask]
    cols = shadow_cols[mask]
    if len(rows) == 0:
        raise ValueError(f"empty region {region_label}")

    row_min, row_max = int(rows.min()), int(rows.max())
    col_min, col_max = int(cols.min()), int(cols.max())
    bbox = BoundingBox(row_min=row_min, row_max=row_max, col_min=col_min, col_max=col_max)
    centroid_row = float(rows.mean())
    centroid_col = float(cols.mean())
    area_px = int(len(rows))

    # Tip: farthest pixel from top-left corner of bbox (approximates shadow end)
    dists = (rows - row_min).astype(np.float64) ** 2 + (cols - col_min).astype(np.float64) ** 2
    farthest = int(np.argmax(dists))
    tip_row, tip_col = int(rows[farthest]), int(cols[farthest])

    return bbox, centroid_row, centroid_col, area_px, tip_row, tip_col


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_shadows(
    rgb: np.ndarray,
    *,
    min_area_px: int = 20,
) -> list[ShadowRegion]:
    """Detect candidate shadow regions in an RGB image.

    Parameters
    ----------
    rgb:
        HxWx3 uint8 NumPy array (BGR or RGB — only luminance is used).
    min_area_px:
        Minimum region area in pixels.  Regions smaller than this are
        discarded (noise filter).  Default 20 px.

    Returns
    -------
    list[ShadowRegion]
        Detected shadow regions sorted by area descending.  May be empty
        when no regions pass the filter (uniform image, no shadow structure).

    Notes
    -----
    Metric shadow lengths are NOT computed here — callers who need metric
    outputs must supply an explicit GSD and call
    ``depthwizard.solar.integrate.solar_observations_from_image()``.
    """
    import numpy as np

    if not isinstance(rgb, np.ndarray):
        raise TypeError(f"rgb must be a numpy ndarray, got {type(rgb).__name__}")
    if rgb.ndim != 3 or rgb.shape[2] < 3:
        raise ValueError(f"rgb must be HxWx3 (or HxWxN with N≥3), got shape {rgb.shape}")
    if rgb.dtype != np.uint8:
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    if min_area_px < 1:
        raise ValueError(f"min_area_px must be ≥ 1, got {min_area_px}")

    h, w = rgb.shape[:2]
    if h == 0 or w == 0:
        return []

    lum = _luminance(rgb[:, :, :3])
    if float(lum.max() - lum.min()) < 15.0:
        return []

    threshold = _otsu_threshold(lum)
    shadow_mask = (lum <= threshold) & (lum < float(np.mean(lum)))
    if not shadow_mask.any():
        return []

    labels = _connected_regions(shadow_mask)
    shadow_rows, shadow_cols = shadow_mask.nonzero()

    # Collect unique non-zero labels
    unique_labels: dict[int, int] = {}
    for lbl in labels[shadow_rows, shadow_cols]:
        if lbl != 0:
            unique_labels[lbl] = unique_labels.get(lbl, 0) + 1

    regions: list[ShadowRegion] = []
    for region_label, area in unique_labels.items():
        if area < min_area_px:
            continue
        bbox, centroid_row, centroid_col, area_px, tip_row, tip_col = _region_stats(
            labels, shadow_rows, shadow_cols, region_label
        )
        # Quality heuristic: large compact regions are "clear"; barely-passing
        # are "uncertain"; very elongated or non-compact are "occluded"
        extent = area_px / max(bbox.height_px * bbox.width_px, 1)
        if area_px < min_area_px * 3:
            quality = "uncertain"
        elif extent < 0.2:
            quality = "occluded"
        else:
            quality = "clear"

        regions.append(
            ShadowRegion(
                region_id=region_label,
                bbox=bbox,
                centroid_row=centroid_row,
                centroid_col=centroid_col,
                area_px=area_px,
                tip_row=tip_row,
                tip_col=tip_col,
                quality=quality,
            )
        )

    regions.sort(key=lambda r: r.area_px, reverse=True)
    return regions


def gsd_from_inspection(inspection: object) -> float | None:
    """Extract ground sampling distance (m/px) from an InputInspection.

    Returns the mean pixel size in metres if the inspection carries a
    georeferenced affine transform, else None.  Callers are responsible
    for deciding whether to proceed without metric output.
    """
    from depthwizard.contracts.spatial import SpatialKind

    spatial = getattr(inspection, "spatial", None)
    if spatial is None or spatial.kind is not SpatialKind.PRESENT:
        return None
    details = spatial.details
    if details is None or details.transform is None:
        return None
    t = details.transform
    # Affine: pixel width = |a|, pixel height = |e|; average for GSD estimate.
    a = getattr(t, "a", None)
    e = getattr(t, "e", None)
    if a is None or e is None:
        return None
    try:
        gsd = (abs(float(a)) + abs(float(e))) / 2.0
        return gsd if math.isfinite(gsd) and gsd > 0.0 else None
    except (TypeError, ValueError):
        return None
