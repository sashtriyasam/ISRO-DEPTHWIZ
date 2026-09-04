"""Tests for target normalization (M7) - mocked backbone, no GPU/weights needed."""

import json
import pytest
from pathlib import Path

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")

from depthwizard.adapt.loss import TargetScale, masked_l1
from depthwizard.adapt.train import _compute_target_stats


# 1-2. TargetScale raw and zscore modes
def test_target_scale_raw_identity():
    ts = TargetScale(mode="raw")
    x = torch.tensor([-5.0, 0.0, 5.0, 10.0, 100.0])
    assert torch.allclose(ts.forward(x), x)
    assert torch.allclose(ts.inverse(x), x)
    assert ts.config()["mode"] == "raw"


def test_target_scale_zscore_forward_inverse():
    ts = TargetScale(mode="zscore", mu=10.0, sigma=5.0)
    x = torch.tensor([5.0, 10.0, 15.0, 20.0])
    z = ts.forward(x)
    expected = torch.tensor([-1.0, 0.0, 1.0, 2.0])
    assert torch.allclose(z, expected)
    # Inverse should recover original
    x_rec = ts.inverse(z)
    assert torch.allclose(x_rec, x)


def test_target_scale_zscore_zero_sigma_raises():
    with pytest.raises(ValueError, match="sigma > 0"):
        TargetScale(mode="zscore", mu=0.0, sigma=0.0)
    with pytest.raises(ValueError, match="sigma > 0"):
        TargetScale(mode="zscore", mu=0.0, sigma=-1.0)


def test_target_scale_invalid_mode_raises():
    with pytest.raises(ValueError, match="Unsupported target mode"):
        TargetScale(mode="invalid")
    with pytest.raises(ValueError, match="Unsupported target mode"):
        TargetScale(mode="minmax")


def test_target_scale_config():
    ts_raw = TargetScale(mode="raw")
    assert ts_raw.config() == {"mode": "raw", "normalization": "none (raw meters)"}
    ts_z = TargetScale(mode="zscore", mu=2.5, sigma=1.5)
    cfg = ts_z.config()
    assert cfg["mode"] == "zscore"
    assert cfg["mu"] == 2.5
    assert cfg["sigma"] == 1.5
    assert cfg["normalization"] == "zscore (train pixels only)"


# 3-4. Train stats computation from train data only
def test_compute_target_stats_from_train_data():
    import numpy as np
    np.random.seed(42)
    samples = [
        {"height": np.random.uniform(0, 10, (16, 16)).astype(np.float32)},
        {"height": np.random.uniform(5, 15, (16, 16)).astype(np.float32)},
    ]
    mean, std = _compute_target_stats(samples)
    assert 0 < mean < 20
    assert std > 0


def test_compute_target_stats_handles_nan_inf():
    import numpy as np
    samples = [
        {"height": np.array([[1.0, np.nan], [np.inf, 5.0]], dtype=np.float32)},
        {"height": np.array([[-5.0, 0.0], [10.0, np.nan]], dtype=np.float32)},
    ]
    mean, std = _compute_target_stats(samples)
    # Valid pixels: 1.0, 5.0, -5.0, 0.0, 10.0 -> mean = 2.2, std ~ 5.5
    assert abs(mean - 2.2) < 0.01
    assert std > 0


def test_compute_target_stats_zero_variance_raises():
    samples = [
        {"height": np.full((16, 16), 5.0, dtype=np.float32)},
    ]
    with pytest.raises(ValueError, match="standard deviation is zero or negative"):
        _compute_target_stats(samples)


def test_compute_target_stats_no_valid_pixels_raises():
    samples = [
        {"height": np.full((4, 4), np.nan, dtype=np.float32)},
        {"height": np.full((4, 4), np.inf, dtype=np.float32)},
    ]
    with pytest.raises(ValueError, match="No valid target pixels"):
        _compute_target_stats(samples)


# 5-6. Normalization/inverse roundtrip and negative target preservation
def test_zscore_normalization_inverse_roundtrip():
    ts = TargetScale(mode="zscore", mu=10.0, sigma=5.0)
    x = torch.tensor([-5.0, 0.0, 5.0, 10.0, 15.0, 20.0, -5.0])  # includes negative
    z = ts.forward(x)
    x_rec = ts.inverse(z)
    assert torch.allclose(x_rec, x)
    # Negative values preserved through forward/inverse
    assert (z < 0).any()  # some normalized values negative
    assert (x_rec < 0).any()  # recovered negatives


def test_masked_l1_with_normalized_targets():
    ts = TargetScale(mode="zscore", mu=5.0, sigma=2.0)
    pred = torch.tensor([[[[0.0, 1.0], [2.0, -1.0]]]])  # normalized predictions
    tgt_raw = torch.tensor([[[[3.0, 5.0], [9.0, 1.0]]]])  # raw targets
    tgt_norm = ts.forward(tgt_raw)
    loss, n_valid = masked_l1(pred, tgt_norm)
    assert n_valid == 4
    # pred: [0,1,2,-1], tgt_norm: [(3-5)/2=-1, (5-5)/2=0, (9-5)/2=2, (1-5)/2=-2]
    # abs diff: [1, 1, 0, 1] -> mean = 0.75
    assert loss.item() == pytest.approx(0.75)


def test_masked_l1_preserves_negatives():
    pred = torch.tensor([[[[-5.0, 0.0], [5.0, 10.0]]]])
    tgt = torch.tensor([[[[-5.0, 0.0], [5.0, 10.0]]]])
    loss, n = masked_l1(pred, tgt)
    assert n == 4 and loss.item() == 0.0


def test_masked_l1_ignores_nonfinite():
    pred = torch.tensor([[[[1.0, float('nan')], [float('inf'), 6.0]]]])
    tgt = torch.tensor([[[[1.0, 2.0], [3.0, 6.0]]]])
    loss, n = masked_l1(pred, tgt)
    assert n == 2  # only finite pairs: (1,1) and (6,6)
    assert loss.item() == pytest.approx((0.0 + 0.0) / 2)


# 7-8. Integration: train_one_epoch with normalized targets
def _fake_backbone():
    class _Scratch(torch.nn.Module):
        def __init__(self):
            super().__init__()
            # output_conv1 expects 64 input channels (from refinenet1 output)
            self.output_conv1 = torch.nn.Conv2d(64, 32, kernel_size=1)

    class _DepthHead(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.scratch = _Scratch()

    class FakeBackbone(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.depth_head = _DepthHead()
            # Add a simple stem to produce 64-channel features
            self.stem = torch.nn.Sequential(
                torch.nn.Conv2d(3, 64, kernel_size=3, padding=1),
                torch.nn.ReLU(inplace=True),
            )

        def forward(self, x):
            # Process through stem to get 64-channel features
            x = self.stem(x)
            # The hook on output_conv1 will capture its INPUT (64 channels)
            return self.depth_head.scratch.output_conv1(x)

    return FakeBackbone()


def _model_with_target_scale(target_scale):
    from depthwizard.adapt.model import AdaptedDepthModel
    from depthwizard.adapt.head import build_head

    torch.manual_seed(0)
    return AdaptedDepthModel(_fake_backbone(), head=build_head(), target_scale=target_scale)


def _rgb(h=16, w=16, seed=0):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, (h, w, 3)).astype(np.uint8)


def test_train_one_epoch_with_zscore(tmp_path):
    from depthwizard.adapt.train import train_one_epoch, _compute_target_stats
    from depthwizard.adapt.head import build_head

    torch.manual_seed(0)
    m = _model_with_target_scale(TargetScale(mode="zscore"))
    # Compute target stats from dummy data
    samples = _tiny(n=2)
    mean, std = _compute_target_stats(samples)
    m.target_scale = TargetScale(mode="zscore", mu=mean, sigma=std)

    opt = torch.optim.SGD([p for p in m.head.parameters() if p.requires_grad], lr=1e-3)
    tr = train_one_epoch(m, samples, opt, target_scale=m.target_scale, out_hw=(16, 16))
    assert tr["loss"] >= 0
    assert tr["n_valid"] > 0


def test_evaluate_split_with_zscore():
    from depthwizard.adapt.train import evaluate_split

    torch.manual_seed(0)
    target_scale = TargetScale(mode="zscore", mu=5.0, sigma=2.0)
    m = _model_with_target_scale(target_scale)
    samples = _tiny(n=3)
    out = evaluate_split(m, samples, target_scale, out_hw=(16, 16))
    assert out["mae"] >= 0
    assert out["n_valid"] > 0


# 9-10. Full training with target_scale and checkpoint
def test_train_adapted_model_with_zscore(tmp_path):
    from depthwizard.adapt.train import train_adapted_model

    torch.manual_seed(0)
    target_scale = TargetScale(mode="zscore")
    m = _model_with_target_scale(target_scale)
    tiny = _tiny(n=2)
    # Need to compute stats for the target scale
    mean, std = _compute_target_stats(tiny)
    target_scale = TargetScale(mode="zscore", mu=mean, sigma=std)
    m = _model_with_target_scale(target_scale)

    s = train_adapted_model(m, tiny, tiny, tmp_path, epochs=2, lr=1e-3, seed=0, target_scale=target_scale, out_hw=(16, 16))
    assert s["epochs"] == 2
    assert len(s["history"]) == 2
    assert s["target_scale"]["mode"] == "zscore"
    assert "mu" in s["target_scale"] and "sigma" in s["target_scale"]
    assert (tmp_path / "checkpoints" / "best.pt").is_file()


def test_train_adapted_model_raw_mode(tmp_path):
    from depthwizard.adapt.train import train_adapted_model

    torch.manual_seed(0)
    target_scale = TargetScale(mode="raw")
    m = _model_with_target_scale(target_scale)
    tiny = _tiny(n=2)

    s = train_adapted_model(m, tiny, tiny, tmp_path, epochs=2, lr=1e-3, seed=0, target_scale=target_scale, out_hw=(16, 16))
    assert s["target_scale"]["mode"] == "raw"


# 11. Checkpoint save/load with target_scale metadata
def test_checkpoint_save_load_with_target_scale(tmp_path):
    from depthwizard.adapt.model import AdaptedDepthModel
    from depthwizard.adapt.head import build_head
    from depthwizard.adapt.train import _compute_target_stats

    torch.manual_seed(0)
    target_scale = TargetScale(mode="zscore")
    m = _model_with_target_scale(target_scale)
    tiny = _tiny()
    mean, std = _compute_target_stats(tiny)
    target_scale = TargetScale(mode="zscore", mu=mean, sigma=std)
    m = _model_with_target_scale(target_scale)

    p = tmp_path / "head.pt"
    m.save_head(p, extra={"target_scale": target_scale.config()})
    m2 = AdaptedDepthModel(_fake_backbone(), head=build_head(), target_scale=TargetScale(mode="raw"))
    payload = m2.load_head(p)
    assert payload["extra"]["target_scale"]["mode"] == "zscore"
    assert "mu" in payload["extra"]["target_scale"] and "sigma" in payload["extra"]["target_scale"]


def test_fresh_init_not_resumed_from_m5(tmp_path):
    from depthwizard.adapt.model import AdaptedDepthModel
    from depthwizard.adapt.head import build_head

    a = _model_with_target_scale(TargetScale(mode="zscore"))
    b = _model_with_target_scale(TargetScale(mode="zscore"))
    # Same seed should produce identical initialization
    for pa, pb in zip(a.head.parameters(), b.head.parameters()):
        assert torch.equal(pa, pb)

    ckpt = Path("experiments/dav2-gamus-head-m5-e01/checkpoints/best.pt")
    if not ckpt.is_file():
        pytest.skip("M5 best checkpoint absent (git-ignored)")
    payload = torch.load(str(ckpt), map_location="cpu", weights_only=False)
    disk = payload["head_state"]
    live = a.head.state_dict()
    assert set(disk) == set(live)
    # Fresh init should differ from M5 best checkpoint
    assert any(not torch.equal(disk[k], live[k]) for k in disk), "fresh init must differ from M5 best"


def _tiny(n=2, h=16, seed=0):
    rng = np.random.default_rng(seed)
    return [
        {
            "image": rng.integers(0, 256, (h, h, 3)).astype(np.uint8),
            "height": rng.uniform(0, 10, (h, h)).astype(np.float32),
        }
        for _ in range(n)
    ]