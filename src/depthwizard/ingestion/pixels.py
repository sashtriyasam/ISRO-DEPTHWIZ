"""Model-ready RGB pixels from an inspected input (single shared loader).

Every backend and the solar analysis read pixels through
:func:`load_model_rgb`, so band selection, radiometric scaling and
validity are decided once:

* **Bands** — GeoTIFFs use declared colour interpretation (red, green,
  blue) when present, so BGR/BGRN products are not colour-swapped;
  otherwise the first three bands are used and the record says so.
* **Scaling** — 8-bit data is used as-is. Wider integer and float data
  (typical 11–16-bit satellite DN) is stretched per band from the 2nd to
  the 98th percentile of valid pixels into 0–255, instead of being
  wrapped modulo 256 by a bare ``astype(uint8)``.
* **Validity** — the dataset mask (nodata, alpha, internal masks) and
  non-finite samples mark invalid pixels; PNG alpha == 0 does the same.
  Backends propagate this as ``DepthResult.valid_mask``.

No resampling, reprojection or orientation change: pixel ``(row, col)``
stays aligned with the inspected raster and its transform.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from depthwizard.errors import InvalidInputError
from depthwizard.ingestion.models import InputInspection

#: Percentile window used to stretch non-8-bit data into 0–255.
STRETCH_PERCENTILES = (2.0, 98.0)


@dataclass(frozen=True)
class ModelRgb:
    """HWC uint8 RGB pixels plus validity and how they were derived."""

    rgb: NDArray[np.uint8]
    valid: NDArray[np.bool_]
    bands: str
    scaling: str
    record: dict[str, str] = field(default_factory=dict)

    @property
    def all_valid(self) -> bool:
        """Whether every pixel is usable."""
        return bool(self.valid.all())

    def valid_mask_tuple(self) -> tuple[bool, ...] | None:
        """Row-major validity for ``DepthResult.valid_mask`` (None when all valid)."""
        if self.all_valid:
            return None
        return tuple(bool(v) for v in self.valid.ravel())

    def preprocessing_record(self) -> dict[str, str]:
        """Entries to merge into a backend's preprocessing record."""
        invalid = int((~self.valid).sum())
        return {
            "input_bands": self.bands,
            "radiometric_scaling": self.scaling,
            "invalid_input_pixels": str(invalid),
        }


def _stretch_to_uint8(
    data: NDArray[np.floating] | NDArray[np.integer], valid: NDArray[np.bool_]
) -> NDArray[np.uint8]:
    """Per-band percentile stretch of (bands, H, W) data into uint8."""
    low_p, high_p = STRETCH_PERCENTILES
    out = np.zeros(data.shape, dtype=np.uint8)
    for index in range(data.shape[0]):
        band = data[index].astype(np.float64)
        usable = valid & np.isfinite(band)
        if not usable.any():
            continue
        low, high = np.percentile(band[usable], [low_p, high_p])
        if not high > low:
            high = low + 1.0
        scaled = (band - low) / (high - low) * 255.0
        scaled = np.where(np.isfinite(scaled), scaled, 0.0)
        out[index] = np.clip(np.rint(scaled), 0, 255).astype(np.uint8)
    return out


def _load_pillow(path: Path, display: str) -> ModelRgb:
    from PIL import Image

    with Image.open(path) as img:
        img.load()
        mode = img.mode
        alpha: NDArray[np.uint8] | None = None
        if "A" in img.getbands():
            alpha = np.array(img.getchannel("A"))
        if mode in ("I;16", "I;16B", "I;16L", "I", "F"):
            raw = np.array(img).astype(np.float64)
            valid = np.isfinite(raw)
            gray = _stretch_to_uint8(raw[np.newaxis, ...], valid)[0]
            rgb = np.stack([gray, gray, gray], axis=-1)
            scaling = f"percentile-{STRETCH_PERCENTILES[0]:g}-{STRETCH_PERCENTILES[1]:g} ({mode})"
            bands = "gray"
        else:
            rgb = np.array(img.convert("RGB"), dtype=np.uint8)
            valid = np.ones(rgb.shape[:2], dtype=bool)
            scaling = "none (8-bit)"
            bands = "rgb"
    if alpha is not None:
        valid = valid & (alpha > 0)
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise InvalidInputError(f"cannot interpret {display} as RGB (shape {rgb.shape})")
    return ModelRgb(rgb=np.ascontiguousarray(rgb), valid=valid, bands=bands, scaling=scaling)


def _select_bands(colorinterp: tuple[str, ...], count: int, display: str) -> tuple[list[int], str]:
    """1-based band indices for R, G, B (or gray) and a description."""
    names = [name.lower() for name in colorinterp]
    if all(colour in names for colour in ("red", "green", "blue")):
        indices = [names.index(colour) + 1 for colour in ("red", "green", "blue")]
        return indices, "declared R,G,B = bands " + ",".join(str(i) for i in indices)
    if count >= 3:
        return [1, 2, 3], "assumed R,G,B = bands 1,2,3 (no colour interpretation declared)"
    if count == 2 and names[1] == "alpha":
        return [1], "gray band 1 (+ alpha)"
    if count == 1:
        return [1], "gray band 1"
    raise InvalidInputError(f"TIFF with {count} bands cannot be interpreted as RGB: {display}")


def _load_rasterio(path: Path, display: str) -> ModelRgb:
    import rasterio

    with rasterio.open(path) as ds:
        colorinterp = tuple(str(ci.name) for ci in ds.colorinterp)
        indices, bands = _select_bands(colorinterp, int(ds.count), display)
        data = ds.read(indices)
        valid = ds.dataset_mask() != 0
    if data.dtype.kind == "f":
        valid = valid & np.isfinite(data).all(axis=0)
    if data.dtype == np.uint8:
        pixels = data
        scaling = "none (8-bit)"
    else:
        pixels = _stretch_to_uint8(data, valid)
        scaling = (
            f"percentile-{STRETCH_PERCENTILES[0]:g}-{STRETCH_PERCENTILES[1]:g} "
            f"per band ({data.dtype})"
        )
    if pixels.shape[0] == 1:
        pixels = np.repeat(pixels, 3, axis=0)
    rgb = np.ascontiguousarray(np.transpose(pixels, (1, 2, 0)))
    return ModelRgb(rgb=rgb, valid=np.ascontiguousarray(valid), bands=bands, scaling=scaling)


def load_model_rgb(inspection: InputInspection) -> ModelRgb:
    """Load HWC uint8 RGB pixels and their validity for model input."""
    path = Path(inspection.handle.source_path)
    display = inspection.handle.display_name
    fmt = inspection.detected_format.value
    if fmt in ("png", "jpeg"):
        return _load_pillow(path, display)
    if fmt == "tiff":
        return _load_rasterio(path, display)
    raise InvalidInputError(f"Unsupported format for RGB loading: {fmt} ({display})")
