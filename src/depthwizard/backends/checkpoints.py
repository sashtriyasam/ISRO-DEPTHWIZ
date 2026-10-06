"""Verified checkpoint loading shared by every torch backend.

Each backend pins its checkpoint's SHA-256. Before this module the pins
were only documentation: ``torch.load`` read whatever file a path or
``DW_*_CKPT`` variable pointed at, with full pickle execution. Now:

* the file hash must match the pin, unless ``DW_ALLOW_UNPINNED_CHECKPOINT=1``
  is set explicitly (e.g. evaluating a freshly trained checkpoint) — the
  outcome is recorded in the depth result's preprocessing record;
* ``torch.load`` runs with ``weights_only=True`` so a checkpoint cannot
  execute code while being unpickled.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from depthwizard.errors import ModelInferenceError

#: Explicit opt-in to load a checkpoint whose hash differs from the pin.
UNPINNED_OVERRIDE_ENV = "DW_ALLOW_UNPINNED_CHECKPOINT"

VERIFIED = "sha256-verified"
UNVERIFIED_OVERRIDE = f"unverified ({UNPINNED_OVERRIDE_ENV}=1)"
INJECTED = "injected model (no checkpoint)"

#: (resolved path, size, mtime) -> digest, so repeat loads skip rehashing.
_DIGEST_CACHE: dict[tuple[str, int, float], str] = {}


def file_sha256(path: Path) -> str:
    """SHA-256 of a file, cached per (path, size, mtime) within the process."""
    stat = path.stat()
    key = (str(path.resolve()), stat.st_size, stat.st_mtime)
    cached = _DIGEST_CACHE.get(key)
    if cached is not None:
        return cached
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    value = digest.hexdigest()
    _DIGEST_CACHE[key] = value
    return value


def verify_checkpoint_file(path: Path, expected_sha256: str, label: str) -> str:
    """Return the verification status, or raise on an unexpected file."""
    actual = file_sha256(path)
    if actual.lower() == expected_sha256.lower():
        return VERIFIED
    if os.environ.get(UNPINNED_OVERRIDE_ENV) == "1":
        return UNVERIFIED_OVERRIDE
    raise ModelInferenceError(
        f"{label} checkpoint {path.name} has sha256 {actual}, expected the pinned "
        f"{expected_sha256.lower()}. Refusing to load an unverified checkpoint; set "
        f"{UNPINNED_OVERRIDE_ENV}=1 to load it deliberately (recorded in provenance)."
    )


def load_checkpoint_state(
    torch: Any, path: Path, expected_sha256: str, label: str
) -> tuple[Any, str]:
    """Verify then load tensors only (no pickle code execution)."""
    status = verify_checkpoint_file(path, expected_sha256, label)
    try:
        state = torch.load(str(path), map_location="cpu", weights_only=True)
    except Exception as exc:
        raise ModelInferenceError(
            f"{label} checkpoint {path.name} could not be loaded as plain tensors "
            f"(weights_only=True): {exc}"
        ) from exc
    return state, status


class DeviceBoundModel:
    """Run upstream DA-V2 ``infer_image`` on the model's own device.

    Upstream ``image2tensor`` moves the input to CUDA whenever CUDA exists,
    regardless of where the model lives, so a CPU-configured backend crashed
    on any GPU machine. This adapter re-homes the tensor before ``forward``.
    """

    def __init__(self, model: Any, device: str) -> None:
        self._model = model
        self._device = device

    def infer_image(self, raw_image: Any, input_size: int = 518) -> Any:
        import torch
        import torch.nn.functional as F

        image, (h, w) = self._model.image2tensor(raw_image, input_size)
        image = image.to(self._device)
        with torch.no_grad():
            depth = self._model.forward(image)
        depth = F.interpolate(depth[:, None], (h, w), mode="bilinear", align_corners=True)[0, 0]
        return depth.cpu().numpy()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._model, name)
