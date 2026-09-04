"""
Depth Anything V2 Small backend — frozen-inference adapter.

Official upstream: https://github.com/DepthAnything/Depth-Anything-V2
Inspected revision: `a561b849ebae10a6f5ef49e26c83cbbcd36c71bf` (HEAD, 2026-03-24).
Checkpoint: HF `depth-anything/Depth-Anything-V2-Small` file
`depth_anything_v2_vits.pth` (sha `03876f8651c73a60fe4c2c48294e09fcb6838fcf`,
Apache-2.0 — the only DA-V2 scale under a permissive license).

The backend consumes the official implementation (`depth_anything_v2.dpt`)
— it is NOT vendored. The package must be importable (pinned clone on
PYTHONPATH or an equivalent install); weights are resolved from an explicit
path, `DW_DAV2_CKPT`, or `checkpoints/depth_anything_v2_vits.pth` and are
never committed. See docs/research/depth-anything-v2.md.

Output semantics: monocular RELATIVE depth (ReLU'd, scale-ambiguous),
restored to source-image size by the official `infer_image` path.
`is_metric=False` always. No calibration, no DSM, no training (Rules A–E).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable, Optional

from depthwizard.depth.base import DepthBackend, DepthResult

MODEL_NAME = "DepthAnythingV2-Small"
ENCODER = "vits"
ENCODER_CONFIG = {"encoder": "vits", "features": 64, "out_channels": [48, 96, 192, 384]}
PARAM_COUNT = 24785089  # verified by construction in M3 bring-up (spec: 24.8M)
CHECKPOINT_FILE = "depth_anything_v2_vits.pth"
CHECKPOINT_HF_ID = "depth-anything/Depth-Anything-V2-Small"
CHECKPOINT_SHA = "03876f8651c73a60fe4c2c48294e09fcb6838fcf"
UPSTREAM_REVISION = "a561b849ebae10a6f5ef49e26c83cbbcd36c71bf"
UPSTREAM_URL = "https://github.com/DepthAnything/Depth-Anything-V2"
DEFAULT_INPUT_SIZE = 518

PREPROCESSING = {
    "entry": "infer_image (official dpt.py, inspected rev a561b84)",
    "input_color": "BGR uint8 HWC (cv2.imread convention); RGB callers are converted RGB->BGR",
    "colorspace_scale": "BGR2RGB then /255.0",
    "resize": "keep_aspect_ratio, lower_bound, ensure_multiple_of=14, INTER_CUBIC",
    "normalize": "ImageNet mean=[0.485,0.456,0.406] std=[0.229,0.224,0.225]",
    "tensor": "PrepareForNet HWC->CHW float32",
    "output_restore": "bilinear interpolate to source (H,W), align_corners=True",
    "dataset_vs_model": "GAMUS loading (M2 experiment interface) is separate from this model preprocessing",
}

VALID_DEVICES = ("cpu", "cuda", "mps")


def default_checkpoint_path() -> Path:
    """Resolve checkpoint: explicit env `DW_DAV2_CKPT` else repo `checkpoints/`."""
    env = os.environ.get("DW_DAV2_CKPT")
    if env:
        return Path(env)
    try:
        project_root = Path(__file__).resolve().parents[3]
        if (project_root / "src").exists():
            return project_root / "checkpoints" / CHECKPOINT_FILE
    except Exception:
        pass
    return Path.cwd() / "checkpoints" / CHECKPOINT_FILE


class DepthAnythingV2Backend(DepthBackend):
    """Frozen Depth Anything V2 Small inference backend (relative depth only).

    Args:
        checkpoint: explicit weights path (default: `default_checkpoint_path()`).
        device: "cpu" | "cuda" | "mps". Unavailable accelerators raise —
            no silent fallback.
        input_size: official inference size (default 518).
        seed: torch manual seed for reproducibility bookkeeping.
        model_factory: injection point for tests
            `factory(encoder_config) -> object with infer_image/load_state_dict/to/eval`.
    """

    def __init__(
        self,
        checkpoint: Optional[Path | str] = None,
        device: str = "cpu",
        input_size: int = DEFAULT_INPUT_SIZE,
        seed: int = 0,
        model_factory: Optional[Callable[[dict], Any]] = None,
    ) -> None:
        if device not in VALID_DEVICES:
            raise ValueError(f"Unknown device {device!r}: expected one of {VALID_DEVICES}")
        if input_size <= 0:
            raise ValueError("input_size must be positive")
        self.checkpoint = Path(checkpoint) if checkpoint is not None else default_checkpoint_path()
        self.device = device
        self.input_size = int(input_size)
        self.seed = int(seed)
        self._factory = model_factory
        self._model: Optional[Any] = None

    @property
    def name(self) -> str:
        return "depth-anything-v2-small"

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def _require_torch(self) -> Any:
        try:
            import torch  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "torch is required for DepthAnythingV2Backend but is not installed. "
                f"Install the 'dav2' extra (pip install -e .[dav2]). Original error: {e}"
            ) from e
        return torch

    def _check_device(self, torch: Any) -> None:
        if self.device == "cuda" and not torch.cuda.is_available():
            raise RuntimeError('device="cuda" requested but torch.cuda.is_available() is False')
        if self.device == "mps" and not getattr(torch.backends, "mps", None):
            raise RuntimeError('device="mps" requested but torch.backends.mps is unavailable')
        if self.device == "mps":
            try:
                if not torch.backends.mps.is_available():
                    raise RuntimeError('device="mps" requested but torch.backends.mps.is_available() is False')
            except RuntimeError:
                raise
            except Exception as e:
                raise RuntimeError(f'device="mps" unavailable: {e}') from e

    def _import_model_class(self) -> Any:
        try:
            from depth_anything_v2.dpt import DepthAnythingV2  # type: ignore
        except Exception as e:
            raise RuntimeError(
                "Official package 'depth_anything_v2' is not importable. Use the pinned upstream clone "
                f"({UPSTREAM_URL} @ {UPSTREAM_REVISION}) on PYTHONPATH — do NOT vendor it into the "
                f"tracked tree. See docs/research/depth-anything-v2.md. Original error: {e}"
            ) from e
        return DepthAnythingV2

    def load(self) -> None:
        """Load checkpoint into memory (idempotent). Raises if missing/unusable."""
        if self._model is not None:
            return
        torch = self._require_torch()
        self._check_device(torch)
        if not self.checkpoint.is_file():
            raise FileNotFoundError(
                f"Depth Anything V2 Small checkpoint not found: {self.checkpoint}. "
                f"Expected HF '{CHECKPOINT_HF_ID}' file '{CHECKPOINT_FILE}' "
                f"(sha {CHECKPOINT_SHA}). Set DW_DAV2_CKPT or place the file under "
                "checkpoints/ (git-ignored). Weights are never committed."
            )
        torch.manual_seed(self.seed)
        if self._factory is not None:
            self._model = self._factory(dict(ENCODER_CONFIG))
            return
        model_cls = self._import_model_class()
        model = model_cls(**ENCODER_CONFIG)
        state = torch.load(str(self.checkpoint), map_location="cpu")
        model.load_state_dict(state)
        model = model.to(self.device).eval()
        self._model = model

    def infer(self, image_rgb: Any) -> DepthResult:
        """Infer relative depth from HWC uint8 RGB. Returns source-sized DepthResult."""
        import numpy as np  # type: ignore

        arr = np.asarray(image_rgb)
        if arr.ndim != 3 or arr.shape[2] != 3:
            raise ValueError(f"Expected HWC RGB with 3 channels, got shape {arr.shape}")
        if arr.dtype != np.uint8:
            raise ValueError(f"Expected uint8 RGB (raw dataset semantics), got {arr.dtype}")
        if self._model is None:
            self.load()
        try:
            import cv2  # type: ignore
        except Exception as e:
            raise RuntimeError(f"opencv-python (cv2) is required for BGR conversion: {e}") from e
        h, w = int(arr.shape[0]), int(arr.shape[1])
        bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        t0 = time.perf_counter()
        depth = self._model.infer_image(bgr, self.input_size)
        dt = time.perf_counter() - t0
        depth = np.asarray(depth)
        if depth.shape != (h, w):
            raise ValueError(f"Backend must restore source size {(h, w)}, got {depth.shape}")
        return DepthResult(
            prediction=depth,
            scale_semantics="relative",
            is_metric=False,
            model_name=MODEL_NAME,
            checkpoint_id=f"{CHECKPOINT_HF_ID}:{CHECKPOINT_FILE}",
            checkpoint_sha=CHECKPOINT_SHA,
            upstream_revision=UPSTREAM_REVISION,
            device=self.device,
            input_size=self.input_size,
            input_shape=(h, w),
            preprocessing=dict(PREPROCESSING),
            inference_time_s=dt,
        )

    def config_dict(self) -> dict[str, Any]:
        try:
            import torch  # type: ignore

            torch_version = getattr(torch, "__version__", "unknown")
        except Exception:
            torch_version = "not installed"
        try:
            ckpt_display = self.checkpoint.relative_to(Path.cwd()).as_posix()
        except Exception:
            ckpt_display = self.checkpoint.as_posix()

        return {
            "backend": self.name,
            "model": MODEL_NAME,
            "encoder": ENCODER,
            "checkpoint_id": f"{CHECKPOINT_HF_ID}:{CHECKPOINT_FILE}",
            "checkpoint_sha": CHECKPOINT_SHA,
            "checkpoint_path": ckpt_display,  # relative to CWD when possible (no personal paths)
            "upstream_revision": UPSTREAM_REVISION,
            "device": self.device,
            "input_size": self.input_size,
            "seed": self.seed,
            "torch_version": torch_version,
        }

    def close(self) -> None:
        self._model = None
