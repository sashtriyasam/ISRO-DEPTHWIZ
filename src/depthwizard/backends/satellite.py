"""Satellite-adapted Depth Anything V2 backend."""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
from numpy.typing import NDArray

from depthwizard.backends.depth_anything_v2 import _load_image_rgb
from depthwizard.contracts.artifacts import DepthResult, ImageResolution
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import DepthScale, ElevationSemantics
from depthwizard.errors import InvalidInputError, ModelInferenceError
from depthwizard.ingestion.models import InputInspection
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
CHECKPOINT_SHA256 = "0" * 64
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
    "tiling": ("overlapping tile grid of 512px with 64px overlap, linear feather blending"),
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
    for top in range(0, h, stride):
        for left in range(0, w, stride):
            bottom = min(top + tile_size, h)
            right = min(left + tile_size, w)
            tile = image_bgr[top:bottom, left:right]
            tile_depth = np.asarray(model.infer_image(tile, input_size), dtype=np.float64)
            th, tw = tile_depth.shape[:2]
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
        for parent_dir in (Path(__file__).resolve().parents[3], Path.cwd()):
            for sub in ("third_party", "deps", ".deps"):
                cand = parent_dir / sub / "Depth-Anything-V2"
                if cand.is_dir() and str(cand) not in sys.path:
                    sys.path.insert(0, str(cand))
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
        model_cls = self._import_model_class()
        model = model_cls(**ENCODER_CONFIG)
        state = torch.load(str(self._checkpoint), map_location="cpu")
        model.load_state_dict(state)
        model = model.to(self._device).eval()
        self._model = model

    def estimate_depth(self, inspection: InputInspection) -> DepthResult:
        if not isinstance(inspection, InputInspection):
            raise InvalidInputError(
                f"SatelliteDepthBackend requires InputInspection, got {type(inspection).__name__}"
            )
        try:
            image_rgb = _load_image_rgb(inspection)
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
            valid_mask=None,
            confidence_values=None,
            preprocessing=dict(PREPROCESSING_RECORD),
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
