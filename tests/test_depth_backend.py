"""Backend boundary tests (no weights; model_factory mocks the torch boundary)."""

import pytest

np = pytest.importorskip("numpy")

from depthwizard.depth.base import DepthBackend, DepthResult  # noqa: E402
from depthwizard.depth.depth_anything_v2 import (  # noqa: E402
    CHECKPOINT_SHA,
    MODEL_NAME,
    DepthAnythingV2Backend,
    default_checkpoint_path,
)


class _FakeModel:
    """Stands in for the official DepthAnythingV2 (no torch needed)."""

    def __init__(self, roughly="gradient"):
        self.roughly = roughly
        self.loaded_from = None

    def infer_image(self, bgr, input_size=518):
        h, w = bgr.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
        return (xx + yy) / (h + w) + 0.5  # deterministic relative-like field


def _factory(store: dict):
    def make(cfg):
        m = _FakeModel()
        store["model"] = m
        return m

    return make


def _rgb(h=16, w=12):
    rng = np.random.default_rng(7)
    return rng.integers(0, 256, (h, w, 3)).astype(np.uint8)


def test_backend_construction_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("DW_DAV2_CKPT", str(tmp_path / "w.pth"))
    be = DepthAnythingV2Backend()
    assert be.name == "depth-anything-v2-small"
    assert be.device == "cpu" and be.input_size == 518 and not be.is_loaded
    assert be.checkpoint == tmp_path / "w.pth"


def test_invalid_device_rejected():
    with pytest.raises(ValueError, match="Unknown device"):
        DepthAnythingV2Backend(device="tpu")


def test_invalid_input_size_rejected():
    with pytest.raises(ValueError):
        DepthAnythingV2Backend(input_size=0)


def test_unavailable_cuda_raises_not_silent():
    be = DepthAnythingV2Backend(device="cuda", model_factory=_factory({}))
    try:
        import torch

        if torch.cuda.is_available():
            pytest.skip("CUDA available; fallback path not testable here")
    except ImportError:
        pass
    with pytest.raises(RuntimeError, match="cuda"):
        be.load()


def test_missing_checkpoint_actionable(tmp_path):
    be = DepthAnythingV2Backend(checkpoint=tmp_path / "absent.pth", model_factory=_factory({}))
    with pytest.raises(FileNotFoundError, match="checkpoint not found"):
        be.load()


def test_missing_official_package_actionable(tmp_path, monkeypatch):
    ckpt = tmp_path / "w.pth"
    ckpt.write_bytes(b"fake")
    be = DepthAnythingV2Backend(checkpoint=ckpt)
    monkeypatch.delitem(__import__("sys").modules, "depth_anything_v2", raising=False)
    monkeypatch.delitem(__import__("sys").modules, "depth_anything_v2.dpt", raising=False)
    # Force import failure by shadowing with a blocker.
    import builtins

    real_import = builtins.__import__

    def blocker(name, *a, **k):
        if name.startswith("depth_anything_v2"):
            raise ImportError("blocked for test")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", blocker)
    with pytest.raises(RuntimeError, match="not importable"):
        be.load()


def test_infer_shape_restoration_and_metadata(tmp_path):
    ckpt = tmp_path / "w.pth"
    ckpt.write_bytes(b"fake")
    store: dict = {}
    be = DepthAnythingV2Backend(checkpoint=ckpt, model_factory=_factory(store))
    res = be.infer(_rgb(16, 12))
    assert isinstance(res, DepthResult)
    assert res.shape == (16, 12)  # source size restored
    assert res.scale_semantics == "relative" and res.is_metric is False
    assert res.model_name == MODEL_NAME and res.checkpoint_sha == CHECKPOINT_SHA
    assert res.input_shape == (16, 12) and res.inference_time_s is not None
    assert res.confidence is None  # DA-V2 provides none
    assert res.finite_coverage == 1.0


def test_infer_rejects_bad_input(tmp_path):
    ckpt = tmp_path / "w.pth"
    ckpt.write_bytes(b"fake")
    be = DepthAnythingV2Backend(checkpoint=ckpt, model_factory=_factory({}))
    with pytest.raises(ValueError):
        be.infer(np.zeros((8, 8), np.uint8))  # not HWC
    with pytest.raises(ValueError):
        be.infer(np.zeros((8, 8, 3), np.float32))  # not uint8


def test_output_size_mismatch_raises(tmp_path):
    ckpt = tmp_path / "w.pth"
    ckpt.write_bytes(b"fake")

    class _WrongSize(_FakeModel):
        def infer_image(self, bgr, input_size=518):
            return np.zeros((4, 4))  # wrong size on purpose

    be = DepthAnythingV2Backend(checkpoint=ckpt, model_factory=lambda cfg: _WrongSize())
    with pytest.raises(ValueError, match="source size"):
        be.infer(_rgb())


def test_result_metric_guardrails():
    pred = np.ones((4, 4))
    with pytest.raises(ValueError, match="calibration_provenance"):
        DepthResult(prediction=pred, scale_semantics="metric", is_metric=True)
    ok = DepthResult(prediction=pred, calibration_provenance="shuttled-to-calibration-v9")
    assert ok.is_metric is False  # relative default retained
    with pytest.raises(NotImplementedError, match="calibration"):
        ok.metric_height()
    with pytest.raises(ValueError):
        DepthResult(prediction=np.ones((4, 4, 1)))  # must be 2D


def test_result_serialization_jsonable(tmp_path):
    import json

    res = DepthResult(prediction=np.array([[0.5, 1.5], [2.0, 3.0]]), model_name=MODEL_NAME, device="cpu")
    d = res.to_dict()
    assert d["scale_semantics"] == "relative" and d["is_metric"] is False
    assert d["pred_min"] == 0.5 and d["shape"] == [2, 2]
    json.dumps(d)  # must be JSON-serializable
    assert "prediction" not in d  # arrays excluded by default


def test_deterministic_config(tmp_path):
    ckpt = tmp_path / "w.pth"
    ckpt.write_bytes(b"fake")
    be = DepthAnythingV2Backend(checkpoint=ckpt, seed=0)
    c1 = be.config_dict()
    c2 = DepthAnythingV2Backend(checkpoint=ckpt, seed=0).config_dict()
    assert c1 == c2
    assert c1["checkpoint_sha"] == CHECKPOINT_SHA


def test_default_checkpoint_path_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("DW_DAV2_CKPT", str(tmp_path / "custom.pth"))
    assert default_checkpoint_path() == tmp_path / "custom.pth"


def test_backend_is_depthbackend_subclass(tmp_path):
    ckpt = tmp_path / "w.pth"
    ckpt.write_bytes(b"fake")
    assert isinstance(DepthAnythingV2Backend(checkpoint=ckpt), DepthBackend)
