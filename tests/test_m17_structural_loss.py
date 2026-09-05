"""Tests for M17 Pearson-distance structural objective (mocked; no GPU, no weights, no downloads)."""

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")


def test_m17_perfect_affine_prediction_scores_zero():
    """pred = 5*target + 10 must yield (near-)zero loss: scale/shift invariance."""
    from depthwizard.adapt.loss import pearson_distance

    tgt = torch.tensor([[[[1.0, 2.0, 4.0, 8.0]]]])
    pred = 5.0 * tgt + 10.0
    loss, n = pearson_distance(pred, tgt)
    assert n == 4
    assert loss.item() == pytest.approx(0.0, abs=1e-6)


def test_m17_perfect_prediction_scores_zero():
    from depthwizard.adapt.loss import pearson_distance

    y = torch.tensor([[[[-3.0, 0.0, 44.5]]]])
    loss, n = pearson_distance(y, y.clone())
    assert n == 3
    assert loss.item() == pytest.approx(0.0, abs=1e-6)


def test_m17_constant_prediction_not_perfect():
    """Constant prediction must yield neutral 1.0, never a misleading perfect score."""
    from depthwizard.adapt.loss import pearson_distance

    pred = torch.full((1, 1, 1, 8), 3.0)
    tgt = torch.tensor([[[[1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]]]])
    loss, n = pearson_distance(pred, tgt)
    assert n == 8
    assert loss.item() == pytest.approx(1.0)


def test_m17_zero_variance_target_handled():
    from depthwizard.adapt.loss import pearson_distance

    pred = torch.tensor([[[[1.0, 2.0, 3.0]]]])
    tgt = torch.full((1, 1, 1, 3), 7.0)
    loss, n = pearson_distance(pred, tgt)
    assert loss.item() == pytest.approx(1.0)


def test_m17_zero_variance_prediction_handled():
    from depthwizard.adapt.loss import pearson_distance

    pred = torch.zeros(1, 1, 1, 5)
    tgt = torch.tensor([[[[1.0, 2.0, 3.0, 4.0, 5.0]]]])
    loss, n = pearson_distance(pred, tgt)
    assert n == 5
    assert loss.item() == pytest.approx(1.0)


def test_m17_masking_ignores_invalid():
    from depthwizard.adapt.loss import pearson_distance

    pred = torch.tensor([[[[1.0, 2.0, float("nan"), 4.0]]]])
    tgt = torch.tensor([[[[2.0, 4.0, 6.0, float("inf")]]]])
    loss, n = pearson_distance(pred, tgt)
    assert n == 2  # only first two pixels valid
    assert loss.item() == pytest.approx(0.0, abs=1e-6)  # exact 2x relation on valid


def test_m17_negative_values_supported():
    from depthwizard.adapt.loss import pearson_distance

    pred = torch.tensor([[[[-5.0, -1.0, 0.0, 9.0]]]])
    tgt = torch.tensor([[[[-10.0, -2.0, 0.0, 18.0]]]])
    loss, n = pearson_distance(pred, tgt)
    assert n == 4
    assert loss.item() == pytest.approx(0.0, abs=1e-6)


def test_m17_tiny_valid_count_raises():
    from depthwizard.adapt.loss import pearson_distance

    with pytest.raises(ValueError):
        pearson_distance(
            torch.tensor([[[[1.0, float("nan")]]]]),
            torch.tensor([[[[2.0, 3.0]]]]),
        )
    with pytest.raises(ValueError):
        pearson_distance(
            torch.full((1, 1, 2, 2), float("nan")),
            torch.zeros(1, 1, 2, 2),
        )


def test_m17_determinism_and_shape_mismatch():
    from depthwizard.adapt.loss import pearson_distance

    rng = torch.Generator().manual_seed(0)
    pred = torch.randn(1, 1, 4, 4, generator=rng)
    tgt = torch.randn(1, 1, 4, 4, generator=torch.Generator().manual_seed(1))
    l1, _ = pearson_distance(pred, tgt)
    l2, _ = pearson_distance(pred, tgt)
    assert l1.item() == pytest.approx(l2.item())
    assert 0.0 <= l1.item() <= 2.0
    with pytest.raises(ValueError):
        pearson_distance(torch.zeros(1, 1, 2, 2), torch.zeros(1, 1, 2, 3))


class _Scratch(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.output_conv1 = torch.nn.Conv2d(64, 32, kernel_size=1)


class _DepthHead(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.scratch = _Scratch()


class _FakeBackbone(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.depth_head = _DepthHead()
        self.proj = torch.nn.Conv2d(3, 64, kernel_size=1)
        self.dummy = torch.nn.Parameter(torch.zeros(4))

    def forward(self, x):
        return self.depth_head.scratch.output_conv1(self.proj(x))


def test_m17_loss_threads_through_trainer(tmp_path):
    """loss='pearson' must train end-to-end via train_adapted_model (tiny synthetic)."""
    from depthwizard.adapt.head import build_head
    from depthwizard.adapt.loss import TargetScale
    from depthwizard.adapt.model import AdaptedDepthModel
    from depthwizard.adapt.train import train_adapted_model

    torch.manual_seed(0)
    model = AdaptedDepthModel(_FakeBackbone(), head=build_head())
    rng = np.random.default_rng(0)
    tr = [{"sample_id": "t0",
           "image": rng.integers(0, 256, (16, 16, 3)).astype(np.uint8),
           "height": rng.normal(100.0, 10.0, (16, 16)).astype(np.float32)}]
    va = [{"sample_id": "v0",
           "image": rng.integers(0, 256, (16, 16, 3)).astype(np.uint8),
           "height": rng.normal(100.0, 10.0, (16, 16)).astype(np.float32)}]
    s = train_adapted_model(
        model, tr, va, tmp_path / "p", epochs=2, lr=1e-3, seed=0,
        selection_metric="pearson", selection_mode="max",
        out_hw=(16, 16), target_scale=TargetScale(mode="raw"), loss="pearson",
    )
    assert s["loss"] == "pearson"
    assert len(s["history"]) == 2
    assert all(np.isfinite(h["train_loss"]) for h in s["history"])
    assert (tmp_path / "p" / "checkpoints" / "best.pt").exists()
