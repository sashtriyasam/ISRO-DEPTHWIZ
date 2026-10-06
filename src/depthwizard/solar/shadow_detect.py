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
5. Identify connected regions (OpenCV ``connectedComponents`` when
   available, otherwise a row-major union-find scan), numbered in
   row-major order of first appearance so results do not depend on which
   labeller ran.
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


def _connected_regions(mask: np.ndarray) -> np.ndarray:
    """Label 4-connected components, numbered by row-major first appearance.

    Uses OpenCV when importable (C speed on multi-megapixel scenes) and the
    pure-Python union-find otherwise; both yield identical label maps.
    """
    import numpy as np

    try:
        import cv2
    except ImportError:
        labels = _connected_regions_python(mask)
    else:
        _count, raw = cv2.connectedComponents(mask.astype(np.uint8), connectivity=4)
        labels = raw.astype(np.int32)
    return _renumber_row_major(labels)


def _renumber_row_major(labels: np.ndarray) -> np.ndarray:
    """Relabel 1..N in order of each component's first row-major pixel."""
    import numpy as np

    flat = labels.ravel()
    present = np.flatnonzero(flat)
    if present.size == 0:
        return labels.astype(np.int32)
    unique, first = np.unique(flat[present], return_index=True)
    order = unique[np.argsort(first, kind="stable")]
    lookup: np.ndarray = np.zeros(int(flat.max()) + 1, dtype=np.int32)
    lookup[order] = np.arange(1, order.size + 1, dtype=np.int32)
    relabelled: np.ndarray = lookup[labels].astype(np.int32)
    return relabelled


def _connected_regions_python(
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
    regions = _collect_regions(labels, min_area_px)
    regions.sort(key=lambda r: r.area_px, reverse=True)
    return regions


def region_pixels(labels: np.ndarray) -> dict[int, tuple[np.ndarray, np.ndarray]]:
    """Map each label to its (rows, cols) pixel arrays in one sorted pass."""
    import numpy as np

    rows, cols = np.nonzero(labels)
    if rows.size == 0:
        return {}
    ids = labels[rows, cols]
    order = np.argsort(ids, kind="stable")
    ids, rows, cols = ids[order], rows[order], cols[order]
    boundaries: np.ndarray = np.flatnonzero(np.diff(ids)) + 1
    starts = np.concatenate(([0], boundaries))
    ends = np.concatenate((boundaries, [ids.size]))
    return {int(ids[s]): (rows[s:e], cols[s:e]) for s, e in zip(starts, ends, strict=True)}


def _collect_regions(labels: np.ndarray, min_area_px: int) -> list[ShadowRegion]:
    """Per-region statistics without per-region full-image scans."""
    import numpy as np

    regions: list[ShadowRegion] = []
    for region_label, (rows, cols) in region_pixels(labels).items():
        area_px = int(rows.size)
        if area_px < min_area_px:
            continue
        row_min, row_max = int(rows.min()), int(rows.max())
        col_min, col_max = int(cols.min()), int(cols.max())
        bbox = BoundingBox(row_min=row_min, row_max=row_max, col_min=col_min, col_max=col_max)
        d_rows: np.ndarray = (rows - row_min).astype(np.float64)
        d_cols: np.ndarray = (cols - col_min).astype(np.float64)
        farthest = int(np.argmax(d_rows**2 + d_cols**2))
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
                centroid_row=float(rows.mean()),
                centroid_col=float(cols.mean()),
                area_px=area_px,
                tip_row=int(rows[farthest]),
                tip_col=int(cols[farthest]),
                quality=quality,
            )
        )
    return regions


def segment_shadows(
    rgb: np.ndarray, *, min_area_px: int = 20
) -> tuple[np.ndarray, list[ShadowRegion]]:
    """Shadow regions plus the label map (for measurements along a direction)."""
    import numpy as np

    if not isinstance(rgb, np.ndarray) or rgb.ndim != 3 or rgb.shape[2] < 3:
        raise ValueError("rgb must be an HxWx3 numpy array")
    if rgb.dtype != np.uint8:
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    h, w = rgb.shape[:2]
    empty = np.zeros((h, w), dtype=np.int32)
    if h == 0 or w == 0:
        return empty, []
    lum = _luminance(rgb[:, :, :3])
    if float(lum.max() - lum.min()) < 15.0:
        return empty, []
    threshold = _otsu_threshold(lum)
    shadow_mask = (lum <= threshold) & (lum < float(np.mean(lum)))
    if not shadow_mask.any():
        return empty, []
    labels = _connected_regions(shadow_mask)
    regions = _collect_regions(labels, min_area_px)
    regions.sort(key=lambda r: r.area_px, reverse=True)
    return labels, regions


def gsd_from_inspection(inspection: object) -> float | None:
    """Ground sampling distance (m/px) from a georeferenced InputInspection.

    Returns ``None`` unless the transform is axis-aligned with square pixels
    and the CRS is projected with metre units: a geographic CRS stores pixel
    size in degrees, which must never be treated as metres.
    """
    from depthwizard.contracts.spatial import SpatialKind

    spatial = getattr(inspection, "spatial", None)
    if spatial is None or spatial.kind is not SpatialKind.PRESENT:
        return None
    details = spatial.details
    if details is None or details.transform is None or details.crs is None:
        return None
    transform = details.transform
    # Contract is GDAL order: x = a + b*col + c*row, y = d + e*col + f*row,
    # so b/f are the pixel sizes and c/e the rotation terms.
    try:
        b, c = float(transform.b), float(transform.c)
        e, f = float(transform.e), float(transform.f)
    except (TypeError, ValueError, AttributeError):
        return None
    if c != 0.0 or e != 0.0 or not math.isclose(abs(b), abs(f), rel_tol=1e-6):
        return None
    from depthwizard.geospatial.crs import crs_is_projected_metric

    if not crs_is_projected_metric(details.crs):
        return None
    gsd = abs(b)
    return gsd if math.isfinite(gsd) and gsd > 0.0 else None


def is_north_up(inspection: object) -> bool:
    """Whether image rows run north to south and columns west to east."""
    from depthwizard.contracts.spatial import SpatialKind

    spatial = getattr(inspection, "spatial", None)
    if spatial is None or spatial.kind is not SpatialKind.PRESENT or spatial.details is None:
        return False
    transform = spatial.details.transform
    if transform is None:
        return False
    # GDAL order: no rotation (c == e == 0), x grows east (b > 0), y shrinks
    # down the rows (f < 0).
    return (
        float(transform.c) == 0.0
        and float(transform.e) == 0.0
        and float(transform.b) > 0.0
        and float(transform.f) < 0.0
    )
