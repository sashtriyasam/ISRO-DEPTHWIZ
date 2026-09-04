"""M4 adaptation tests (mocked backbone; no GPU, no weights, no downloads)."""

import json

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")

from depthwizard.adapt.evaluate import evaluate_predictions  # noqa: E402
from depthwizard.adapt.features import (  # noqa: E402
    FEATURE_CHANNELS,
    FEATURE_TAP,
    capture_features,
    freeze_backbone,
    preprocess_rgb,
    resolve_tap,
)
from depthwizard.adapt.head import build_head, count_parameters, forward_head  # noqa: E402
from depthwizard.adapt.loss import TargetScale, masked_l1  # noqa: E402
from depthwizard.adapt.model import AdaptedDepthModel  # noqa: E402


class _Scratch(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.output_conv1 = torch.nn.Conv2d(64, 32, kernel_size=1)


class _DepthHead(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.scratch = _Scratch()


class FakeBackbone(torch.nn.Module):
    """Mock frozen backbone exposing the M4 tap path (no weights needed)."""

    def __init__(self):
        super().__init__()
        self.depth_head = _DepthHead()
        self.proj = torch.nn.Conv2d(3, 64, kernel_size=1)  # stands in for upstream fusion
        self.dummy = torch.nn.Parameter(torch.zeros(4))

    def forward(self, x):
        # Hook on output_conv1 captures its INPUT (64ch), mirroring the real tap.
        return self.depth_head.scratch.output_conv1(self.proj(x))


def _rgb(h=32, w=32, seed=0):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, (h, w, 3)).astype(np.uint8)


def _model(seed=0):
    torch.manual_seed(seed)
    return AdaptedDepthModel(FakeBackbone(), head=build_head())


# 1-2. Frozen backbone / trainable head.
def test_backbone_frozen_head_trainable():
    m = _model()
    assert all(not p.requires_grad for p in m.backbone.parameters())
    assert any(p.requires_grad for p in m.head.parameters())
    m.assert_frozen()
    rep = m.parameter_report()
    assert rep["backbone_trainable"] == 0 and rep["head_trainable"] > 0
    assert rep["total"] == rep["backbone_total"] + rep["head_total"]


def test_freeze_backbone_counts():
    out = freeze_backbone(FakeBackbone())
    assert out["trainable"] == 0 and out["frozen"] == out["total"] > 0


# 3-4. Forward shape + spatial alignment.
def test_forward_shape_and_alignment():
    m = _model()
    out = m.forward(_rgb(), out_hw=(32, 32))
    assert tuple(out.shape) == (1, 32, 32)
    pred = m.predict_height(_rgb(), out_hw=(32, 32))
    assert np.asarray(pred).shape == (32, 32)


def test_forward_head_channel_guard():
    m = _model()
    bad = torch.zeros(1, 32, 8, 8)
    with pytest.raises(ValueError, match="64 input channels"):
        forward_head(m.head_holder, bad)


def test_feature_tap_resolution_and_docs():
    assert FEATURE_TAP == "depth_head.scratch.output_conv1"
    assert FEATURE_CHANNELS == 64
    mod = FakeBackbone()
    assert resolve_tap(mod) is mod.depth_head.scratch.output_conv1
    with pytest.raises(AttributeError):
        resolve_tap(mod, "depth_head.nope")
    x = preprocess_rgb(_rgb())
    assert x.shape[0] == 1 and x.shape[1] == 3
    feat = capture_features(mod, x)
    assert feat.shape[1] == 64 and feat.ndim == 4 and not feat.requires_grad


# 5-7. Loss masking, negatives, invalid values.
def test_masked_l1_ignores_nonfinite():
    pred = torch.tensor([[[[1.0, 2.0], [3.0, 4.0]]]])
    tgt = torch.tensor([[[[1.0, float("nan")], [float("inf"), 6.0]]]])
    loss, n = masked_l1(pred, tgt)
    assert n == 2 and loss.item() == pytest.approx((0.0 + 2.0) / 2)


def test_negative_targets_preserved():
    pred = torch.zeros(1, 1, 2, 2)
    tgt = torch.full((1, 1, 2, 2), -5.0)  # M2 sentinel candidate stays a valid target
    loss, n = masked_l1(pred, tgt)
    assert n == 4 and loss.item() == pytest.approx(5.0)


def test_zero_valid_raises_not_fake_zero():
    with pytest.raises(ValueError, match="zero valid"):
        masked_l1(torch.full((1, 1, 2, 2), float("nan")), torch.zeros(1, 1, 2, 2))
    with pytest.raises(ValueError, match="shape"):
        masked_l1(torch.zeros(1, 1, 2, 2), torch.zeros(1, 1, 3, 3))


# 8. Gradient flow: head gets grads, backbone none.
def test_training_step_gradient_flow():
    m = _model()
    opt = torch.optim.SGD([p for p in m.head.parameters() if p.requires_grad], lr=1e-3)
    opt.zero_grad()
    pred = m.forward(_rgb(), out_hw=(16, 16)).unsqueeze(0)
    tgt = torch.rand_like(pred) * 30
    loss, _ = masked_l1(pred, tgt)
    loss.backward()
    assert all(p.grad is not None for p in m.head.parameters() if p.requires_grad)
    assert all(p.grad is None for p in m.backbone.parameters())
    opt.step()


# 9. Checkpoint save/load roundtrip (+16 metadata).
def test_checkpoint_roundtrip(tmp_path):
    m = _model(seed=1)
    before = [p.detach().clone() for p in m.head.parameters()]
    p = m.save_head(tmp_path / "best.pt", extra={"epoch": 3})
    m2 = _model(seed=99)
    payload = m2.load_head(p)
    for a, b in zip(before, m2.head.parameters()):
        assert torch.equal(a, b)
    assert payload["feature_tap"] == FEATURE_TAP
    assert "nDSM" in payload["output_semantics"] or "ndsm" in payload["output_semantics"].lower()
    assert payload["extra"] == {"epoch": 3}


# 10. Deterministic subset selection (M1 machinery reused).
def test_deterministic_subset_reused():
    from depthwizard.data.schemas import GamusRecord
    from depthwizard.data.subset import select_development_subset

    recs = [
        GamusRecord(sample_id=f"DC_{i:02d}", image_path=f"images/train/DC_{i:02d}_RGB.h5",
                    height_path=f"heights/train/DC_{i:02d}_AGL.h5",
                    label_path=f"classes/train/DC_{i:02d}_CLS.h5", split="train")
        for i in range(6)
    ]
    a = select_development_subset(recs, size=2, seed="m4-debug")
    b = select_development_subset(list(reversed(recs)), size=2, seed="m4-debug")
    assert [r.sample_id for r in a] == [r.sample_id for r in b]


# 11. Train/val separation guard.
def test_train_val_overlap_guard(tmp_path):
    from depthwizard.experiments.adapt_dav2 import _records
    import json as _json

    rec = {"sample_id": "DC_01", "image_path": "images/train/DC_01_RGB.h5", "height_path": "h", "label_path": None, "split": "train"}
    mp = tmp_path / "m.json"
    mp.write_text(_json.dumps({"version": "1.0", "source": "gamus", "root": ".", "records": [rec]}), encoding="utf-8")
    assert [r.sample_id for r in _records(mp, "train")] == ["DC_01"]
    assert _records(mp, "val") == []


# 12-13. Raw-meter scale contract + inverse identity.
def test_raw_meter_scale_identity():
    sc = TargetScale("raw")
    t = torch.tensor([[[[-5.0, 0.0, 44.5]]]])
    assert torch.equal(sc.forward(t), t) and torch.equal(sc.inverse(t), t)
    assert sc.config()["normalization"].startswith("none")
    with pytest.raises(ValueError, match="raw meters only"):
        TargetScale("zscore")


def test_training_uses_raw_meters():
    pred = torch.tensor([[[[10.0, 20.0]]]])
    tgt = torch.tensor([[[[12.0, 17.0]]]])
    loss, _ = masked_l1(pred, tgt)
    assert loss.item() == pytest.approx(2.5)  # no scaling, no normalization


# 14. Metric calculations incl. per-class + bins.
def test_evaluate_predictions_known_values():
    pred = [np.array([[1.0, 2.0], [3.0, 4.0]])]
    tgt = [np.array([[1.0, 4.0], [3.0, 8.0]])]
    lab = [np.array([[3.0, 3.0], [1.0, 1.0]])]
    out = evaluate_predictions(pred, tgt, labels=lab, class_names={3: "buildings", 1: "ground"})
    assert out["error"]["mae"] == pytest.approx(1.5)
    assert out["n_valid"] == 4
    assert out["per_class"]["buildings"]["mae"] == pytest.approx(1.0)
    assert out["per_class"]["ground"]["mae"] == pytest.approx(2.0)
    assert out["height_bins"]["1-5m"]["n"] == 3
    assert out["correlation"]["pearson"] is not None


def test_evaluate_missing_class_not_zero_filled():
    out = evaluate_predictions([np.zeros((2, 2))], [np.ones((2, 2))], labels=[np.zeros((2, 2))])
    assert "water" not in out["per_class"]


# 15. Train summary JSON-serializable with selection metadata.
def test_train_summary_serializable(tmp_path):
    from depthwizard.adapt.train import evaluate_split, train_adapted_model

    m = _model()
    tiny = [
        {"image": _rgb(16, 16, seed=i), "height": (np.random.default_rng(i).uniform(0, 5, (16, 16))).astype(np.float32)}
        for i in range(2)
    ]
    s = train_adapted_model(m, tiny, tiny, tmp_path, epochs=1, lr=1e-3, seed=0, out_hw=(16, 16))
    assert s["best_epoch"] == 0 and "history" in s
    json.loads((tmp_path / "train_summary.json").read_text(encoding="utf-8"))
    assert (tmp_path / "checkpoints" / "best.pt").is_file()
    va = evaluate_split(m, tiny, out_hw=(16, 16))
    assert va["mae"] >= 0 and va["n_valid"] == 2 * 256


# 17. Semantics: adapted = GAMUS metric; 18. M3 backend untouched.
def test_semantics_split():
    m = _model()
    assert "nDSM" in m.output_semantics or "ndsm" in m.output_semantics.lower()
    from depthwizard.depth.depth_anything_v2 import DepthAnythingV2Backend

    assert not hasattr(DepthAnythingV2Backend, "head")
    assert "relative" in DepthAnythingV2Backend.__doc__


def test_head_param_counts_lightweight():
    n = count_parameters(build_head().module)
    assert n["trainable"] < 100_000  # lightweight claim quantified
    assert n["frozen"] == 0
