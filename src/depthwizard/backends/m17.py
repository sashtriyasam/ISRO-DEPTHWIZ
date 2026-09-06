"""M17 GeoNRW structural-adaptation backend — canonical adapter.

Frozen research candidate (``origin/feat/shravan-final-ml-release``):
DA-V2-Small frozen backbone + M10-initialized 23k Pearson-adapted head
(``experiments/m17-geonrw-struct-e01/checkpoints/best.pt``, epoch 6).

Provenance fields are separated:
- ``UPSTREAM_REVISION``: git commit hash of the pinned upstream repo
  (same DA-V2 pin as the canonical adapter).
- ``CHECKPOINT_SHA256``: SHA-256 of the M17 ``best.pt`` file itself.
- ``M10_BASE_SHA256`` / ``GEONRW_SET_SHA``: adaptation lineage, carried
  in the semantic-meaning record (the canonical provenance contract is
  unchanged — no new fields).

The M17 head implementation is NOT vendored here.  With an injected
``model_factory`` (tests, deterministic fakes) the backend runs the
frozen M17 preprocessing path end to end.  Without a factory, the real
path requires torch, the pinned upstream source, the M17 head code and
the ``best.pt`` checkpoint; anything missing raises loudly — never a
silent fallback, never synthetic substitution.

Output semantics: monocular RELATIVE geometric representation
(scale-ambiguous), following the source image grid.  ``is_metric`` is
never True.  No calibration, no DSM, no training.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from depthwizard.backends.depth_anything_v2 import _load_image_rgb
from depthwizard.contracts.artifacts import DepthResult, ImageResolution
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import DepthScale, ElevationSemantics
from depthwizard.errors import InvalidInputError, ModelInferenceError
from depthwizard.ingestion.models import InputInspection
from depthwizard.version import __version__

MODEL_NAME = "M17-GeoNRW-Struct"
MODEL_VERSION = "17.6"
BACKEND_ID = "m17-geonrw-struct"
ENCODER = "vits+frozen-head-23k"
CHECKPOINT_FILE = "m17_geonrw_struct_best.pt"
CHECKPOINT_SHA256 = "D7C0BE9127FAFAC5F4C2D207E3626D335AF148A8CBB7489A10EE8C7F7DA4EDAC"
M10_BASE_SHA256 = "B3DFD54F"
GEONRW_SET_SHA = "012c318944ef205f"
GEONRW_REVISION = "eeb5fc3e"
UPSTREAM_REVISION = "a561b849ebae10a6f5ef49e26c83cbbcd36c71bf"
UPSTREAM_URL = "https://github.com/DepthAnything/Depth-Anything-V2"
DEFAULT_INPUT_SIZE = 518
PARAM_COUNT = 24_785_089 + 23_201

#: Frozen M10 z-score statistics for head I/O (mu, sigma).  Values are
#: part of the frozen candidate definition — never recomputed here.
M10_ZMU = 8.037330237035235
M10_ZSIGMA = 10.304011604437477

PREPROCESSING_RECORD: dict[str, str] = {
    "entry": "m17_geonrw_struct (frozen M17 preprocessing, rev a561b84 backbone)",
    "input_color": "RGB uint8 HWC, first-3 channels (RGBI slice)",
    "colorspace_scale": "ImageNet mean/std, then frozen M10 zscore",
    "resize": "ImageNet/518 pipeline, output pinned to source grid (no resampling of results)",
    "normalize": f"zscore with frozen M10 mu={M10_ZMU} sigma={M10_ZSIGMA}",
    "tensor": "HWC->CHW float32 (real path)",
    "output_restore": "source grid (H,W); nodata->NaN; finite mask; negatives kept",
}

VALID_DEVICES = ("cpu", "cuda", "mps")
CHECKPOINT_ENV = "DW_M17_CKPT"


def _default_checkpoint_path() -> Path:
    """Resolve checkpoint: explicit env ``DW_M17_CKPT`` else repo ``checkpoints/``."""
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


class M17DepthBackend:
    """Frozen M17 GeoNRW structural-adaptation inference backend.

    Implements the canonical :class:`DepthBackend` protocol with the
    frozen M17 preprocessing path.  Model-specific details stay inside
    this adapter; the rest of DepthWizard remains model-agnostic.

    Args:
        checkpoint: explicit weights path (default: ``_default_checkpoint_path()``).
        device: ``"cpu"`` | ``"cuda"`` | ``"mps"``.  Unavailable accelerators
            raise — no silent fallback.
        input_size: inference size (default 518).
        seed: torch manual seed for reproducibility bookkeeping.
        model_factory: injection point for tests —
            ``factory() -> object with infer_image``.
    """

    def __init__(
        self,
        checkpoint: Path | str | None = None,
        device: str = "cpu",
        input_size: int = DEFAULT_INPUT_SIZE,
        seed: int = 0,
        model_factory: Callable[[], Any] | None = None,
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
        return "m17-geonrw-struct"

    @property
    def model_version(self) -> str | None:
        return MODEL_VERSION

    @property
    def checkpoint_id(self) -> str | None:
        return f"m17-geonrw-struct-e01:{CHECKPOINT_FILE}"

    def _require_torch(self) -> Any:
        try:
            import torch
        except Exception as e:
            raise ModelInferenceError(
                "torch is required for M17DepthBackend but is not installed. "
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

    def load(self) -> None:
        """Load checkpoint into memory (idempotent). Raises if missing/unusable."""
        if self._model is not None:
            return
        torch = self._require_torch()
        self._check_device(torch)
        if not self._checkpoint.is_file():
            raise ModelInferenceError(
                f"M17 checkpoint not found: {self._checkpoint}. "
                f"Expected M17 'best.pt' (sha256 {CHECKPOINT_SHA256}). "
                f"Set {CHECKPOINT_ENV} or place the file under "
                "checkpoints/ (git-ignored). Weights are never committed."
            )
        torch.manual_seed(self._seed)
        if self._factory is not None:
            self._model = self._factory()
            return
        raise ModelInferenceError(
            "M17 head implementation is not available in this checkout. "
            "The M17 23k Pearson-adapted head is research code outside the "
            "canonical tree; provide it via model_factory (tests) or a "
            "future sanctioned adapter. No synthetic substitution performed."
        )

    def estimate_depth(self, inspection: InputInspection) -> DepthResult:
        """Run frozen M17 inference on a validated input inspection.

        Produces a canonical :class:`DepthResult` with ``RELATIVE`` scale.
        Frozen M17 preprocessing (first-3 channels, ImageNet/518, frozen
        M10 zscore) is applied with NumPy; the model itself runs behind
        the injected factory (or the real head when available).
        """
        import numpy as np

        if not isinstance(inspection, InputInspection):
            raise InvalidInputError(
                f"M17DepthBackend requires an InputInspection, got {type(inspection).__name__}"
            )

        try:
            image_rgb = _load_image_rgb(inspection)
        except InvalidInputError:
            raise
        except Exception as e:
            raise ModelInferenceError(f"Failed to load image for M17 inference: {e}") from e

        h, w = int(image_rgb.shape[0]), int(image_rgb.shape[1])

        if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
            raise InvalidInputError(
                f"Expected HWC RGB with 3 channels, got shape {image_rgb.shape}"
            )
        if image_rgb.dtype != np.uint8:
            raise InvalidInputError(f"Expected uint8 RGB, got dtype {image_rgb.dtype}")

        if self._model is None:
            self.load()

        # Frozen M17 preprocessing: first-3 channels, ImageNet normalize,
        # frozen M10 zscore — NumPy only, deterministic.
        image_f = image_rgb.astype(np.float64) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float64)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float64)
        normalized = (image_f - mean) / std
        features = (normalized.mean(axis=2) - M10_ZMU) / M10_ZSIGMA

        t0 = time.perf_counter()
        depth = self._model.infer_image(features, self._input_size)
        _ = time.perf_counter() - t0

        depth = np.asarray(depth, dtype=np.float64)
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
                    "relative_depth from M17 GeoNRW structural adaptation "
                    "(frozen inference; M10 base "
                    f"{M10_BASE_SHA256}, GeoNRW set {GEONRW_SET_SHA})"
                ),
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
            "m10_base_sha256": M10_BASE_SHA256,
            "geonrw_set_sha": GEONRW_SET_SHA,
            "geonrw_revision": GEONRW_REVISION,
            "device": self._device,
            "input_size": self._input_size,
            "seed": self._seed,
            "torch_version": torch_version,
        }
