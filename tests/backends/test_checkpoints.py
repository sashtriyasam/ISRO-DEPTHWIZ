"""Checkpoint pins are enforced and torch.load never unpickles code."""

import hashlib
from pathlib import Path
from typing import Any

import pytest

from depthwizard.backends.checkpoints import (
    UNPINNED_OVERRIDE_ENV,
    UNVERIFIED_OVERRIDE,
    VERIFIED,
    load_checkpoint_state,
)
from depthwizard.backends.depth_anything_v2 import DepthAnythingV2Backend
from depthwizard.errors import ModelInferenceError


class _RecordingTorch:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    def load(self, path: str, **kwargs: Any) -> dict[str, str]:
        self.kwargs = kwargs
        return {"weights": "ok"}


def _file(tmp_path: Path, payload: bytes = b"weights") -> tuple[Path, str]:
    path = tmp_path / "model.pth"
    path.write_bytes(payload)
    return path, hashlib.sha256(payload).hexdigest()


def test_matching_hash_loads_tensors_only(tmp_path: Path) -> None:
    path, digest = _file(tmp_path)
    torch = _RecordingTorch()
    state, status = load_checkpoint_state(torch, path, digest.upper(), "test-model")
    assert state == {"weights": "ok"}
    assert status == VERIFIED
    assert torch.kwargs["weights_only"] is True
    assert torch.kwargs["map_location"] == "cpu"


def test_mismatched_hash_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(UNPINNED_OVERRIDE_ENV, raising=False)
    path, _ = _file(tmp_path)
    torch = _RecordingTorch()
    with pytest.raises(ModelInferenceError, match="Refusing to load an unverified"):
        load_checkpoint_state(torch, path, "0" * 64, "test-model")
    assert torch.kwargs == {}


def test_override_loads_and_is_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(UNPINNED_OVERRIDE_ENV, "1")
    path, _ = _file(tmp_path)
    _state, status = load_checkpoint_state(_RecordingTorch(), path, "0" * 64, "test-model")
    assert status == UNVERIFIED_OVERRIDE


def test_backend_refuses_tampered_checkpoint_before_torch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytest.importorskip("torch")
    monkeypatch.delenv(UNPINNED_OVERRIDE_ENV, raising=False)
    path, _ = _file(tmp_path, b"not the pinned weights")
    backend = DepthAnythingV2Backend(checkpoint=path)
    with pytest.raises(ModelInferenceError, match="sha256"):
        backend.load()
