"""Depth Anything V2 Small backend — canonical adapter.

Official upstream: https://github.com/DepthAnything/Depth-Anything-V2
Pinned revision: ``a561b849ebae10a6f5ef49e26c83cbbcd36c71bf`` (HEAD, 2026-03-24).
Checkpoint: HF ``depth-anything/Depth-Anything-V2-Small`` file
``depth_anything_v2_vits.pth``
Apache-2.0 — the only DA-V2 scale under a permissive license.

Provenance fields are separated:
- ``UPSTREAM_REVISION``: git commit hash of the pinned upstream repo.
- ``CHECKPOINT_SHA256``: SHA-256 hash of the checkpoint file itself.

The backend consumes the official implementation (``depth_anything_v2.dpt``)
— it is NOT vendored.  The package must be importable (pinned clone on
PYTHONPATH or an equivalent install); weights are resolved from an explicit
path, ``DW_DAV2_CKPT``, or ``checkpoints/depth_anything_v2_vits.pth`` and
are never committed.

Output semantics: monocular RELATIVE depth (scale-ambiguous), restored to
source-image size by the official ``infer_image`` path.  ``is_metric``
is never True.  No calibration, no DSM, no training.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from depthwizard.contracts.artifacts import DepthResult, ImageResolution
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import DepthScale, ElevationSemantics
from depthwizard.errors import InvalidInputError, ModelInferenceError
from depthwizard.ingestion.models import InputInspection
from depthwizard.version import __version__

if TYPE_CHECKING:
    import numpy as np

MODEL_NAME = "DepthAnythingV2-Small"
MODEL_VERSION = "2.0.0"
ENCODER = "vits"
ENCODER_CONFIG: dict[str, Any] = {
    "encoder": "vits",
    "features": 64,
    "out_channels": [48, 96, 192, 384],
}
CHECKPOINT_FILE = "depth_anything_v2_vits.pth"
CHECKPOINT_HF_ID = "depth-anything/Depth-Anything-V2-Small"
CHECKPOINT_SHA256 = "715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378"
UPSTREAM_REVISION = "a561b849ebae10a6f5ef49e26c83cbbcd36c71bf"
UPSTREAM_URL = "https://github.com/DepthAnything/Depth-Anything-V2"
DEFAULT_INPUT_SIZE = 518
PARAM_COUNT = 24_785_089

PREPROCESSING_RECORD: dict[str, str] = {
    "entry": "infer_image (official dpt.py, inspected rev a561b84)",
    "input_color": "BGR uint8 HWC (cv2.imread convention); RGB callers are converted RGB->BGR",
    "colorspace_scale": "BGR2RGB then /255.0",
    "resize": "keep_aspect_ratio, lower_bound, ensure_multiple_of=14, INTER_CUBIC",
    "normalize": "ImageNet mean=[0.485,0.456,0.406] std=[0.229,0.224,0.225]",
    "tensor": "PrepareForNet HWC->CHW float32",
    "output_restore": "bilinear interpolate to source (H,W), align_corners=True",
}

VALID_DEVICES = ("cpu", "cuda", "mps")


def _default_checkpoint_path() -> Path:
    """Resolve checkpoint: explicit env ``DW_DAV2_CKPT`` else repo ``checkpoints/``."""
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


def _load_image_rgb(inspection: InputInspection) -> np.ndarray:
    """Load image pixels as HWC uint8 RGB from the inspected input.

    Uses Pillow for PNG/JPEG, rasterio for TIFF.  Returns a numpy array
    without storing it on the inspection object.  Model-specific
    preprocessing (BGR conversion, normalization) belongs to the model
    adapter, not here.
    """
    import numpy as np

    path = Path(inspection.handle.source_path)
    fmt = inspection.detected_format

    if fmt.value in ("png", "jpeg"):
        from PIL import Image

        with Image.open(path) as img:
            img.load()
            if img.mode != "RGB":
                rgb_img = img.convert("RGB")
                return np.array(rgb_img, dtype=np.uint8)
            return np.array(img, dtype=np.uint8)

    if fmt.value == "tiff":
        import rasterio

        with rasterio.open(path) as ds:
            bands = ds.count
            if bands == 3:
                data = ds.read((1, 2, 3))  # (3, H, W)
            elif bands >= 3:
                data = ds.read((1, 2, 3))  # take first 3 bands
            elif bands == 1:
                gray = ds.read(1)  # (H, W)
                return np.stack([gray, gray, gray], axis=-1).astype(np.uint8)
            else:
                raise InvalidInputError(
                    f"TIFF with {bands} bands cannot be interpreted as RGB: "
                    f"{inspection.handle.display_name}"
                )
            # rasterio returns (bands, H, W) — transpose to (H, W, bands)
            return np.transpose(data, (1, 2, 0)).astype(np.uint8)  # type: ignore[no-any-return]

    raise InvalidInputError(
        f"Unsupported format for DA-V2 inference: {fmt.value} ({inspection.handle.display_name})"
    )


class DepthAnythingV2Backend:
    """Frozen Depth Anything V2 Small inference backend (relative depth only).

    Implements the canonical :class:`DepthBackend` protocol.  Model-specific
    preprocessing is internal; the rest of DepthWizard remains model-agnostic.

    Args:
        checkpoint: explicit weights path (default: ``_default_checkpoint_path()``).
        device: ``"cpu"`` | ``"cuda"`` | ``"mps"``.  Unavailable accelerators
            raise — no silent fallback.
        input_size: official inference size (default 518).
        seed: torch manual seed for reproducibility bookkeeping.
        model_factory: injection point for tests —
            ``factory(encoder_config) -> object with infer_image / load_state_dict / to.eval``.
    """

    def __init__(
        self,
        checkpoint: Path | str | None = None,
        device: str = "cpu",
        input_size: int = DEFAULT_INPUT_SIZE,
        seed: int = 0,
        model_factory: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        if device not in VALID_DEVICES:
            raise ValueError(f"Unknown device {device!r}: expected one of {VALID_DEVICES}")
        if input_size <= 0:
            raise ValueError("input_size must be positive")
        self._checkpoint = (
            Path(checkpoint) if checkpoint is not None else _default_checkpoint_path()
        )
        self._device = device
        self._input_size = int(input_size)
        self._seed = int(seed)
        self._factory = model_factory
        self._model: Any = None

    @property
    def model_name(self) -> str:
        return "depth-anything-v2-small"

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
            raise ModelInferenceError(
                "torch is required for DepthAnythingV2Backend but is not installed. "
                f"Install the 'dav2' extra (pip install -e .[dav2]). Original error: {e}"
            ) from e
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
        try:
            from depth_anything_v2.dpt import DepthAnythingV2
        except Exception as e:
            raise ModelInferenceError(
                "Official package 'depth_anything_v2' is not importable. "
                f"Use the pinned upstream clone ({UPSTREAM_URL} @ {UPSTREAM_REVISION}) "
                f"on PYTHONPATH — do NOT vendor it into the tracked tree. "
                f"Original error: {e}"
            ) from e
        return DepthAnythingV2

    def load(self) -> None:
        """Load checkpoint into memory (idempotent). Raises if missing/unusable."""
        if self._model is not None:
            return
        torch = self._require_torch()
        self._check_device(torch)
        if not self._checkpoint.is_file():
            raise ModelInferenceError(
                f"Depth Anything V2 Small checkpoint not found: {self._checkpoint}. "
                f"Expected HF '{CHECKPOINT_HF_ID}' file '{CHECKPOINT_FILE}' "
                f"(sha256 {CHECKPOINT_SHA256}). Set DW_DAV2_CKPT or place the file under "
                "checkpoints/ (git-ignored). Weights are never committed."
            )
        torch.manual_seed(self._seed)
        if self._factory is not None:
            self._model = self._factory(dict(ENCODER_CONFIG))
            return
        model_cls = self._import_model_class()
        model = model_cls(**ENCODER_CONFIG)
        state = torch.load(str(self._checkpoint), map_location="cpu")
        model.load_state_dict(state)
        model = model.to(self._device).eval()
        self._model = model

    def estimate_depth(self, inspection: InputInspection) -> DepthResult:
        """Run frozen inference on a validated input inspection.

        Produces a canonical :class:`DepthResult` with ``RELATIVE`` scale.
        The model does not perform geospatial processing; source spatial
        metadata is passed through unchanged.
        """
        import numpy as np

        if not isinstance(inspection, InputInspection):
            raise InvalidInputError(
                f"DepthAnythingV2Backend requires an InputInspection, "
                f"got {type(inspection).__name__}"
            )

        # Load image as HWC uint8 RGB
        try:
            image_rgb = _load_image_rgb(inspection)
        except InvalidInputError:
            raise
        except Exception as e:
            raise ModelInferenceError(f"Failed to load image for DA-V2 inference: {e}") from e

        h, w = int(image_rgb.shape[0]), int(image_rgb.shape[1])

        # Validate image shape
        if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
            raise InvalidInputError(
                f"Expected HWC RGB with 3 channels, got shape {image_rgb.shape}"
            )
        if image_rgb.dtype != np.uint8:
            raise InvalidInputError(f"Expected uint8 RGB, got dtype {image_rgb.dtype}")

        # Ensure model is loaded
        if self._model is None:
            self.load()

        # Model-specific preprocessing: RGB -> BGR for cv2 convention
        try:
            import cv2
        except Exception as e:
            raise ModelInferenceError(
                f"opencv-python (cv2) is required for BGR conversion: {e}"
            ) from e

        bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

        # Inference
        t0 = time.perf_counter()
        depth = self._model.infer_image(bgr, self._input_size)
        _ = time.perf_counter() - t0

        depth = np.asarray(depth)
        if depth.shape != (h, w):
            raise ModelInferenceError(
                f"Backend must restore source size {(h, w)}, got {depth.shape}"
            )

        # Flatten to row-major tuple for the canonical contract
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
                semantic_meaning="relative_depth from Depth Anything V2 Small (frozen inference)",
            ),
        )

    def close(self) -> None:
        """Release model reference (does not guarantee GPU memory reclaim)."""
        self._model = None

    def config_dict(self) -> dict[str, Any]:
        """Structured metadata for service capability reporting."""
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
            "seed": self._seed,
            "torch_version": torch_version,
        }
