"""Satellite-adapted Depth Anything V2 backend."""

from __future__ import annotations

import math
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray

from depthwizard.backends.checkpoints import (
    INJECTED,
    DeviceBoundModel,
    load_checkpoint_state,
)
from depthwizard.contracts.artifacts import DepthResult, ImageResolution
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import DepthScale, ElevationSemantics
from depthwizard.errors import InvalidInputError, ModelInferenceError
from depthwizard.ingestion.models import InputInspection
from depthwizard.ingestion.pixels import load_model_rgb
from depthwizard.version import __version__

if TYPE_CHECKING:
    pass

MODEL_NAME = "SatelliteAdaptation-DepthAnythingV2"
MODEL_VERSION = "2.0.0sat"
BACKEND_ID = "depth-anything-v2-satellite"
ENCODER = "vits"
ENCODER_CONFIG = {"encoder": "vits", "features": 64, "out_channels": [48, 96, 192, 384]}
CHECKPOINT_FILE = "depth_anything_v2_satellite.pth"
CHECKPOINT_HF_ID = "depth-anything/Depth-Anything-V2-Small"
CHECKPOINT_SHA256 = "41520832bbc5c865490a9f84880a3997902a4ae15f5864e026c3d8eae89d14d6"
UPSTREAM_REVISION = "a561b849ebae10a6f5ef49e26c83cbbcd36c71bf"
UPSTREAM_URL = "https://github.com/DepthAnything/Depth-Anything-V2"
DEFAULT_INPUT_SIZE = 518
PARAM_COUNT = 24_785_089
TILE_SIZE = 512
TILE_OVERLAP = 64
PREPROCESSING_RECORD = {
    "entry": ("infer_image (official dpt.py, rev a561b84) with tiling for large satellite imagery"),
    "input_color": ("BGR uint8 HWC (cv2.imread); RGB callers converted RGB->BGR"),
    "colorspace_scale": "BGR2RGB then /255.0",
    "resize": ("keep_aspect, lower_bound, ensure_multiple_of=14, INTER_CUBIC"),
    "normalize": ("ImageNet mean=[0.485,0.456,0.406] std=[0.229,0.224,0.225]"),
    "tensor": "PrepareForNet HWC->CHW float32",
    "output_restore": (
        "bilinear interpolate to tile (H,W), align_corners=True; "
        "tiles blended via linear feathering at overlap; "
        "final stitched to source (H,W)"
    ),
    "tiling": (
        "overlapping 512px tiles (64px overlap, last tile snapped to the edge); "
        "each tile aligned to the mosaic by a least-squares scale+shift fit on "
        "its overlap, then linearly feather-blended"
    ),
}
VALID_DEVICES = ("cpu", "cuda", "mps")
CHECKPOINT_ENV = "DW_DAV2_SAT_CKPT"


def _default_checkpoint_path() -> Path:
    env = os.environ.get(CHECKPOINT_ENV)
    if env:
        return Path(env)
    try:
        project_root = Path(__file__).resolve().parents[3]
        if (project_root / "src").exists():
            return project_root / "checkpoints" / CHECKPOINT_FILE
    except Exception:
        pass
    return Path.cwd() / "checkpoints" / CHECKPOINT_FILE


def _feather_weight(n: int) -> NDArray[np.float64]:
    return (np.arange(n) + 0.5) / n


def _tile_starts(length: int, tile_size: int, stride: int) -> list[int]:
    """Tile origins covering ``length`` with full-size tiles (no slivers).

    The last tile is snapped to end exactly at ``length`` so every tile the
    model sees is ``tile_size`` long (when the image is that large).
    """
    if length <= tile_size:
        return [0]
    starts = list(range(0, length - tile_size, stride))
    starts.append(length - tile_size)
    return sorted(set(starts))


#: Minimum overlap samples needed to fit a scale+shift alignment.
_MIN_ALIGN_SAMPLES = 16


def _align_to_mosaic(
    tile_depth: NDArray[np.float64],
    mosaic: NDArray[np.float64],
    covered: NDArray[np.bool_],
) -> tuple[NDArray[np.float64], float, float]:
    """Map a tile's relative depth onto the mosaic frame via its overlap.

    Each tile is an independent affine-invariant prediction (own scale and
    shift). Fitting ``mosaic ≈ s * tile + o`` on the already-covered overlap
    puts every tile in one consistent relative frame before blending. With
    too little or degenerate overlap, a shift-only (median) alignment is used.
    """
    overlap = covered & np.isfinite(tile_depth) & np.isfinite(mosaic)
    if not overlap.any():
        return tile_depth, 1.0, 0.0
    x = tile_depth[overlap]
    y = mosaic[overlap]
    scale, offset = 1.0, float(np.median(y - x))
    if x.size >= _MIN_ALIGN_SAMPLES:
        x_var = float(np.var(x))
        if x_var > 1e-12:
            fitted = float(np.mean((x - x.mean()) * (y - y.mean())) / x_var)
            if math.isfinite(fitted) and fitted > 0.0:
                scale = fitted
                offset = float(y.mean() - scale * x.mean())
    return tile_depth * scale + offset, scale, offset


def _tiled_infer_image(
    model: Any,
    image_bgr: NDArray[np.uint8],
    input_size: int,
    tile_size: int = TILE_SIZE,
    overlap: int = TILE_OVERLAP,
) -> NDArray[np.float32]:
    h, w = image_bgr.shape[:2]
    if h <= tile_size and w <= tile_size:
        depth = np.asarray(model.infer_image(image_bgr, input_size), dtype=np.float64)
        if depth.shape != (h, w):
            raise ModelInferenceError(
                f"Backend must restore source size {(h, w)}, got {depth.shape}"
            )
        return depth.astype(np.float32)

    stride = tile_size - overlap
    depth_sum = np.zeros((h, w), dtype=np.float64)
    weight_sum = np.zeros((h, w), dtype=np.float64)
    for top in _tile_starts(h, tile_size, stride):
        for left in _tile_starts(w, tile_size, stride):
            bottom = min(top + tile_size, h)
            right = min(left + tile_size, w)
            tile = image_bgr[top:bottom, left:right]
            tile_depth = np.asarray(model.infer_image(tile, input_size), dtype=np.float64)
            th, tw = tile_depth.shape[:2]
            if (th, tw) != (bottom - top, right - left):
                raise ModelInferenceError(
                    f"Tile inference must restore tile size {(bottom - top, right - left)}, "
                    f"got {(th, tw)}"
                )
            window_weight = weight_sum[top:bottom, left:right]
            covered = window_weight > 0
            current = np.divide(
                depth_sum[top:bottom, left:right],
                window_weight,
                out=np.full((th, tw), np.nan),
                where=covered,
            )
            tile_depth, _scale, _offset = _align_to_mosaic(tile_depth, current, covered)
            weight = np.ones((th, tw), dtype=np.float64)
            if top > 0:
                r = min(overlap, th)
                weight[:r, :] *= _feather_weight(r)[:, np.newaxis]
            if bottom < h:
                r = min(overlap, th)
                weight[-r:, :] *= _feather_weight(r)[::-1][:, np.newaxis]
            if left > 0:
                r = min(overlap, tw)
                weight[:, :r] *= _feather_weight(r)[np.newaxis, :]
            if right < w:
                r = min(overlap, tw)
                weight[:, -r:] *= _feather_weight(r)[::-1][np.newaxis, :]
            depth_sum[top:bottom, left:right] += tile_depth * weight
            weight_sum[top:bottom, left:right] += weight

    weight_sum = np.where(weight_sum > 0, weight_sum, 1.0)
    depth_map = depth_sum / weight_sum
    if depth_map.shape != (h, w):
        raise ModelInferenceError(
            f"Tiled inference must restore source size {(h, w)}, got {depth_map.shape}"
        )
    return depth_map.astype(np.float32)


class SatelliteDepthBackend:
    """Satellite-adapted DA-V2 Small with tiling inference."""

    def __init__(
        self,
        checkpoint: Path | str | None = None,
        device: str = "cpu",
        input_size: int = DEFAULT_INPUT_SIZE,
        tile_size: int = TILE_SIZE,
        overlap: int = TILE_OVERLAP,
        seed: int = 0,
        model_factory: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        if device not in VALID_DEVICES:
            raise ValueError(f"Unknown device {device!r}: expected one of {VALID_DEVICES}")
        if input_size <= 0:
            raise ValueError("input_size must be positive")
        if tile_size <= 0:
            raise ValueError("tile_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= tile_size:
            raise ValueError("overlap must be less than tile_size")

        self._checkpoint = (
            Path(checkpoint) if checkpoint is not None else _default_checkpoint_path()
        )
        self._device = device
        self._input_size = int(input_size)
        self._tile_size = int(tile_size)
        self._overlap = int(overlap)
        self._seed = int(seed)
        self._factory = model_factory
        self._model: Any = None
        self._checkpoint_status = INJECTED if model_factory is not None else "not loaded"

    @property
    def model_name(self) -> str:
        return BACKEND_ID

    @property
    def model_version(self) -> str | None:
        return MODEL_VERSION

    @property
    def checkpoint_id(self) -> str | None:
        return f"{CHECKPOINT_HF_ID}:{CHECKPOINT_FILE}"

    def _require_torch(self) -> Any:
        try:
            import torch
        except Exception as e:
            raise ModelInferenceError(f"torch required for SatelliteDepthBackend: {e}") from e
        return torch

    def _check_device(self, torch: Any) -> None:
        if self._device == "cuda" and not torch.cuda.is_available():
            raise ModelInferenceError(
                'device="cuda" requested but torch.cuda.is_available() is False'
            )
        if self._device == "mps":
            try:
                if not torch.backends.mps.is_available():
                    raise ModelInferenceError(
                        'device="mps" requested but torch.backends.mps.is_available() is False'
                    )
            except ModelInferenceError:
                raise
            except Exception as e:
                raise ModelInferenceError(f'device="mps" unavailable: {e}') from e

    def _import_model_class(self) -> Any:
        from depthwizard.runtime.diagnostics import ensure_dav2_source_on_path

        ensure_dav2_source_on_path()
        try:
            from depth_anything_v2.dpt import DepthAnythingV2
        except Exception as e:
            raise ModelInferenceError(
                "Official depth_anything_v2 not importable. "
                "Use pinned upstream clone on PYTHONPATH. "
                f"Error: {e}"
            ) from e
        return DepthAnythingV2

    def load(self) -> None:
        if self._model is not None:
            return
        if self._factory is not None:
            self._model = self._factory(dict(ENCODER_CONFIG))
            return
        if not self._checkpoint.is_file():
            raise ModelInferenceError(
                f"Satellite checkpoint not found: {self._checkpoint}. "
                f"Expected {CHECKPOINT_FILE} (sha256 {CHECKPOINT_SHA256}). "
                f"Set {CHECKPOINT_ENV} or place under checkpoints/."
            )
        torch = self._require_torch()
        self._check_device(torch)
        torch.manual_seed(self._seed)
        state, self._checkpoint_status = load_checkpoint_state(
            torch, self._checkpoint, CHECKPOINT_SHA256, self.model_name
        )
        model_cls = self._import_model_class()
        model = model_cls(**ENCODER_CONFIG)
        if isinstance(state, dict) and "model" in state:
            state = state["model"]
        model.load_state_dict(state)
        model = model.to(self._device).eval()
        self._model = DeviceBoundModel(model, self._device)

    def estimate_depth(self, inspection: InputInspection) -> DepthResult:
        if not isinstance(inspection, InputInspection):
            raise InvalidInputError(
                f"SatelliteDepthBackend requires InputInspection, got {type(inspection).__name__}"
            )
        try:
            loaded = load_model_rgb(inspection)
            image_rgb = loaded.rgb
        except InvalidInputError:
            raise
        except Exception as e:
            raise ModelInferenceError(f"Failed to load image: {e}") from e

        h, w = int(image_rgb.shape[0]), int(image_rgb.shape[1])
        if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
            raise InvalidInputError(f"Expected HWC RGB 3 channels, got {image_rgb.shape}")
        if image_rgb.dtype != np.uint8:
            raise InvalidInputError(f"Expected uint8 RGB, got {image_rgb.dtype}")
        if self._model is None:
            self.load()

        try:
            import cv2

            bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        except ImportError:
            bgr = image_rgb[:, :, ::-1]

        t0 = time.perf_counter()
        depth = _tiled_infer_image(
            self._model, bgr, self._input_size, self._tile_size, self._overlap
        )
        _ = time.perf_counter() - t0
        depth = np.asarray(depth)
        if depth.shape != (h, w):
            raise ModelInferenceError(
                f"Backend must restore source size {(h, w)}, got {depth.shape}"
            )
        depth_values = tuple(float(v) for v in depth.flatten())
        input_res = ImageResolution(width=w, height=h)
        handle = inspection.handle
        return DepthResult(
            model_name=self.model_name,
            model_version=self.model_version,
            checkpoint_id=self.checkpoint_id,
            input_resolution=input_res,
            output_resolution=input_res,
            depth_scale=DepthScale.RELATIVE,
            elevation_semantics=ElevationSemantics.RELATIVE_DEPTH,
            georeferencing=inspection.georeferencing,
            depth_values=depth_values,
            valid_mask=loaded.valid_mask_tuple(),
            confidence_values=None,
            preprocessing={
                **PREPROCESSING_RECORD,
                **loaded.preprocessing_record(),
                "checkpoint_verification": self._checkpoint_status,
            },
            units=None,
            spatial=inspection.spatial,
            provenance=ProductProvenance(
                source_input_id=handle.display_name,
                input_checksum=handle.sha256,
                model_name=self.model_name,
                model_version=self.model_version,
                checkpoint_id=self.checkpoint_id,
                software_version=__version__,
                generated_at=None,
                units=None,
                semantic_meaning=(
                    "relative_depth from satellite-adapted DA-V2 Small "
                    "(fine-tuned on orthophoto imagery; "
                    "DA-V2 loss preserves scale ambiguity)"
                ),
            ),
        )

    def close(self) -> None:
        self._model = None

    def config_dict(self) -> dict[str, Any]:
        try:
            import torch

            torch_version = getattr(torch, "__version__", "unknown")
        except Exception:
            torch_version = "not installed"
        try:
            ckpt_display = self._checkpoint.relative_to(Path.cwd()).as_posix()
        except Exception:
            ckpt_display = self._checkpoint.as_posix()
        return {
            "backend": self.model_name,
            "model": MODEL_NAME,
            "encoder": ENCODER,
            "param_count": PARAM_COUNT,
            "checkpoint_id": self.checkpoint_id,
            "checkpoint_sha256": CHECKPOINT_SHA256,
            "checkpoint_path": ckpt_display,
            "upstream_url": UPSTREAM_URL,
            "upstream_revision": UPSTREAM_REVISION,
            "device": self._device,
            "input_size": self._input_size,
            "tile_size": self._tile_size,
            "tile_overlap": self._overlap,
            "seed": self._seed,
            "torch_version": torch_version,
        }
