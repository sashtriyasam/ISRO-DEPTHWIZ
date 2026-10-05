"""Height backend: DA-V2 Small fine-tuned to predict nDSM (metres above ground).

Trained by ``scripts/train_ndsm.py`` on open airborne LiDAR (RGB -> DSM-DTM)
across 0.35-2 m ground sampling distances. Inference runs tiled at the
image's native resolution (no resizing: apparent object size is part of
what the model reads), with linear feathering between tiles. Predictions
are already metric, so tiles are not re-aligned.

Contract: the output stays ``DepthScale.RELATIVE`` (no metric claim without
a reference) but its preprocessing record declares
``height_units = meters_above_ground``. DEM-anchored fusion then adds the
predicted structure to the reference DEM with a fixed scale of 1 instead of
fitting one, and relative (non-georeferenced) runs show heights on a
plausible scale.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from depthwizard.backends.checkpoints import (
    INJECTED,
    UNPINNED_OVERRIDE_ENV,
    file_sha256,
    load_checkpoint_state,
)
from depthwizard.contracts.artifacts import DepthResult, ImageResolution
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import DepthScale, ElevationSemantics
from depthwizard.errors import InvalidInputError, ModelInferenceError
from depthwizard.ingestion.models import InputInspection
from depthwizard.ingestion.pixels import load_model_rgb
from depthwizard.version import __version__

BACKEND_ID = "depthwizard-ndsm-vits"
MODEL_VERSION = "1.0.0"
CHECKPOINT_FILE = "depthwizard_ndsm_vits.pth"
CHECKPOINT_ENV = "DW_NDSM_CKPT"
#: Pinned when a checkpoint is promoted (see docs/benchmarks); verified at load.
CHECKPOINT_SHA256 = "0" * 64
ENCODER_CONFIG = {"encoder": "vits", "features": 64, "out_channels": [48, 96, 192, 384]}
TILE = 392
OVERLAP = 56
HEIGHT_UNITS_KEY = "height_units"
HEIGHT_UNITS = "meters_above_ground"
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def default_checkpoint_path() -> Path:
    """``DW_NDSM_CKPT``, else the data dir, else the repo ``checkpoints/``."""
    env = os.environ.get(CHECKPOINT_ENV)
    if env:
        return Path(env)
    from depthwizard.runtime.diagnostics import default_data_dir

    provisioned = default_data_dir() / "checkpoints" / CHECKPOINT_FILE
    if provisioned.is_file():
        return provisioned
    return Path(__file__).resolve().parents[3] / "checkpoints" / CHECKPOINT_FILE


def checkpoint_usable(path: Path | None = None) -> bool:
    """True when the checkpoint exists and would pass verification at load.

    Used to decide whether to advertise/auto-select the backend, so an
    unpinned or tampered file never becomes the default model silently.
    """
    path = path or default_checkpoint_path()
    if not path.is_file():
        return False
    if os.environ.get(UNPINNED_OVERRIDE_ENV) == "1":
        return True
    return file_sha256(path).lower() == CHECKPOINT_SHA256.lower()


def _starts(length: int, tile: int, stride: int) -> list[int]:
    if length <= tile:
        return [0]
    starts = list(range(0, length - tile, stride))
    starts.append(length - tile)
    return sorted(set(starts))


def _feather(n: int) -> NDArray[np.float64]:
    return (np.arange(n) + 0.5) / n


def tiled_predict(
    predict: Callable[[NDArray[np.float32]], NDArray[np.float32]],
    rgb: NDArray[np.uint8],
    tile: int = TILE,
    overlap: int = OVERLAP,
) -> NDArray[np.float32]:
    """Run ``predict`` on normalised tiles (multiple-of-14 padded) and blend."""
    h, w = rgb.shape[:2]
    norm = ((rgb.astype(np.float32) / 255.0) - MEAN) / STD
    out = np.zeros((h, w), dtype=np.float64)
    weight = np.zeros((h, w), dtype=np.float64)
    stride = tile - overlap
    for top in _starts(h, tile, stride):
        for left in _starts(w, tile, stride):
            patch = norm[top : top + tile, left : left + tile]
            ph, pw = patch.shape[:2]
            pad_h, pad_w = (-ph) % 14, (-pw) % 14
            if pad_h or pad_w:
                patch = np.pad(patch, ((0, pad_h), (0, pad_w), (0, 0)), mode="reflect")
            pred = np.asarray(predict(patch), dtype=np.float64)[:ph, :pw]
            wgt = np.ones((ph, pw))
            if top > 0:
                r = min(overlap, ph)
                wgt[:r] *= _feather(r)[:, None]
            if top + ph < h:
                r = min(overlap, ph)
                wgt[-r:] *= _feather(r)[::-1][:, None]
            if left > 0:
                r = min(overlap, pw)
                wgt[:, :r] *= _feather(r)[None, :]
            if left + pw < w:
                r = min(overlap, pw)
                wgt[:, -r:] *= _feather(r)[::-1][None, :]
            out[top : top + ph, left : left + pw] += pred * wgt
            weight[top : top + ph, left : left + pw] += wgt
    return (out / np.where(weight > 0, weight, 1.0)).astype(np.float32)


class NdsmBackend:
    """Fine-tuned DA-V2 Small height model (implements ``DepthBackend``)."""

    def __init__(
        self,
        checkpoint: Path | str | None = None,
        device: str = "cpu",
        model_factory: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self._checkpoint = Path(checkpoint) if checkpoint else default_checkpoint_path()
        self._device = device
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
        return f"depthwizard:{CHECKPOINT_FILE}"

    def load(self) -> None:
        if self._model is not None:
            return
        if self._factory is not None:
            self._model = self._factory(dict(ENCODER_CONFIG))
            return
        if not self._checkpoint.is_file():
            raise ModelInferenceError(
                f"nDSM height checkpoint not found: {self._checkpoint}. Set {CHECKPOINT_ENV} "
                "or run scripts/train_ndsm.py."
            )
        import torch

        from depthwizard.runtime.diagnostics import ensure_dav2_source_on_path

        ensure_dav2_source_on_path()
        from depth_anything_v2.dpt import DepthAnythingV2

        state, self._checkpoint_status = load_checkpoint_state(
            torch, self._checkpoint, CHECKPOINT_SHA256, self.model_name
        )
        model = DepthAnythingV2(**ENCODER_CONFIG)
        model.load_state_dict(state["model"] if "model" in state else state)
        if self._device == "cuda" and not torch.cuda.is_available():
            raise ModelInferenceError('device="cuda" requested but CUDA is unavailable')
        self._model = model.to(self._device).eval()

    def _predict(self, patch: NDArray[np.float32]) -> NDArray[np.float32]:
        if self._factory is not None:
            return np.asarray(self._model(patch), dtype=np.float32)
        import torch

        x = torch.from_numpy(np.ascontiguousarray(patch.transpose(2, 0, 1)))[None].to(self._device)
        with torch.no_grad():
            y = self._model(x)
        return y[0].float().cpu().numpy()

    def estimate_depth(self, inspection: InputInspection) -> DepthResult:
        if not isinstance(inspection, InputInspection):
            raise InvalidInputError(
                f"NdsmBackend requires an InputInspection, got {type(inspection).__name__}"
            )
        loaded = load_model_rgb(inspection)
        if self._model is None:
            self.load()
        heights = tiled_predict(self._predict, loaded.rgb)
        heights = np.clip(np.nan_to_num(heights, nan=0.0), 0.0, None)
        h, w = heights.shape
        resolution = ImageResolution(width=w, height=h)
        handle = inspection.handle
        return DepthResult(
            model_name=self.model_name,
            model_version=self.model_version,
            checkpoint_id=self.checkpoint_id,
            input_resolution=resolution,
            output_resolution=resolution,
            depth_scale=DepthScale.RELATIVE,
            elevation_semantics=ElevationSemantics.RELATIVE_DEPTH,
            georeferencing=inspection.georeferencing,
            depth_values=tuple(float(v) for v in heights.ravel()),
            valid_mask=loaded.valid_mask_tuple(),
            confidence_values=None,
            preprocessing={
                "entry": f"tiled native-resolution inference ({TILE}px, {OVERLAP}px overlap)",
                "normalize": "ImageNet mean/std on 0-1 RGB",
                HEIGHT_UNITS_KEY: HEIGHT_UNITS,
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
                semantic_meaning="learned height above ground (nDSM metres); relative "
                "until anchored to a reference",
            ),
        )

    def close(self) -> None:
        self._model = None

    def config_dict(self) -> dict[str, Any]:
        return {
            "backend": self.model_name,
            "checkpoint_sha256": CHECKPOINT_SHA256,
            "checkpoint_path": self._checkpoint.as_posix(),
            "device": self._device,
            "tile": TILE,
            "overlap": OVERLAP,
        }
