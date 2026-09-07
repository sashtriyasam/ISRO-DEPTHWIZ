"""Tests for the production M17 head inference path (no training code involved)."""

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")

from depthwizard.backends.m17_head import (  # noqa: E402
    HEAD_PARAM_COUNT,
    build_head,
    count_head_parameters,
    predict_meters,
    preprocess_rgb,
)


class _Scratch(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.output_conv1 = torch.nn.Conv2d(64, 32, kernel_size=1)


class _DepthHead(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.scratch = _Scratch()


class _FakeBackbone(torch.nn.Module):
    """Stand-in backbone exposing the M17 feature tap."""

    def __init__(self):
        super().__init__()
        self.depth_head = _DepthHead()
        self.proj = torch.nn.Conv2d(3, 64, kernel_size=1)

    def forward(self, x):
        return self.depth_head.scratch.output_conv1(self.proj(x))


def _rgb(h=24, w=32, seed=0):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, (h, w, 3)).astype(np.uint8)


def test_head_param_count_matches_frozen_candidate():
    assert count_head_parameters(build_head()) == HEAD_PARAM_COUNT == 23201


def test_preprocess_rejects_non_rgb():
    with pytest.raises(ValueError):
        preprocess_rgb(np.zeros((8, 8), dtype=np.uint8))
    with pytest.raises(ValueError):
        preprocess_rgb(np.zeros((8, 8, 4), dtype=np.uint8))


def test_predict_meters_shape_finite_and_deterministic():
    torch.manual_seed(0)
    backbone, head = _FakeBackbone(), build_head()
    out1 = predict_meters(backbone, head, _rgb(), out_hw=(12, 16))
    out2 = predict_meters(backbone, head, _rgb(), out_hw=(12, 16))
    assert out1.shape == (12, 16)
    assert np.isfinite(out1).all()
    assert np.array_equal(out1, out2)


def test_predict_meters_channel_guard():
    from depthwizard.backends import m17_head

    class BadBackbone(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.depth_head = _DepthHead()
            # Identity tap: the hook captures whatever flows in (7ch here).
            self.depth_head.scratch.output_conv1 = torch.nn.Identity()

        def forward(self, x):
            return self.depth_head.scratch.output_conv1(torch.zeros(1, 7, 4, 4, device=x.device))

    with pytest.raises(ValueError, match="64"):
        m17_head.capture_features(BadBackbone(), _rgb())


def test_m17_backend_missing_checkpoint_raises_loudly(tmp_path):
    from depthwizard.backends.m17 import M17DepthBackend
    from depthwizard.errors import ModelInferenceError

    backend = M17DepthBackend(checkpoint=tmp_path / "absent.pt")
    with pytest.raises(ModelInferenceError, match="not found"):
        backend.load()


def test_m17_backend_hash_mismatch_raises(tmp_path):
    from depthwizard.backends.m17 import M17DepthBackend
    from depthwizard.errors import ModelInferenceError

    bad = tmp_path / "bad.pt"
    torch.save({"head_state": {}}, str(bad))
    backend = M17DepthBackend(checkpoint=bad)
    with pytest.raises(ModelInferenceError, match="[Hh]ash mismatch"):
        backend.load()


def test_m17_backend_factory_path_unchanged():
    """The injected-factory path keeps its exact legacy behavior."""
    from depthwizard.backends.m17 import M17DepthBackend

    calls = {}

    class Fake:
        def infer_image(self, features, input_size):
            calls["shape"] = getattr(features, "shape", None)
            return np.full((4, 5), 2.0)

    backend = M17DepthBackend(checkpoint=__file__, model_factory=Fake)
    backend.load()
    assert calls == {}
