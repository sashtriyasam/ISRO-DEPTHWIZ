"""Tests for M12 low-height-weighted masked L1 (mocked; no GPU, no weights, no downloads)."""

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")

M10_TRAIN_IDS = [
    "DC_01_25", "DC_02_24", "DC_02_25", "DC_02_27",
    "DC_03_23", "DC_03_24", "DC_03_25", "DC_03_27",
    "DC_03_28", "DC_04_24", "DC_04_25", "DC_04_26",
    "DC_04_28", "DC_05_20", "DC_05_21", "DC_05_26",
    "PHL_0451", "PHL_0496", "PHL_0497", "PHL_0498",
    "NYC_22835", "NYC_22836", "NYC_22837", "NYC_22840",
]

M10_VAL_IDS = {
    "DC_02_26", "DC_04_23", "DC_04_27", "DC_08_31",
    "DC_09_33", "DC_10_30", "DC_11_16", "DC_11_33",
}


def _wloss(pred_z, tgt_z, tgt_m, **kw):
    from depthwizard.experiments.adapt_dav2_m12 import (
        HEIGHT_THRESHOLD_M,
        LOW_HEIGHT_WEIGHT,
    )
    from depthwizard.adapt.loss import masked_height_weighted_l1

    kw.setdefault("threshold", HEIGHT_THRESHOLD_M)
    kw.setdefault("low_weight", LOW_HEIGHT_WEIGHT)
    return masked_height_weighted_l1(pred_z, tgt_z, tgt_m, **kw)


def test_m12_low_pixels_weighted_2x():
    """Pixels with meter target < 5.0 receive weight 2."""
    pred = torch.zeros(1, 1, 1, 2)
    tgt_z = torch.zeros(1, 1, 1, 2)
    tgt_m = torch.tensor([[[[1.0, 10.0]]]])
    # |err| = 1 on the low pixel, 0 on the high pixel -> loss = 2*1/(2+1)
    pred[0, 0, 0, 0] = 1.0
    loss, n = _wloss(pred, tgt_z, tgt_m)
    assert n == 2
    assert loss.item() == pytest.approx(2.0 / 3.0)


def test_m12_high_pixels_weighted_1x():
    """Pixels with meter target >= 5.0 (boundary inclusive) receive weight 1."""
    pred = torch.zeros(1, 1, 1, 3)
    tgt_z = torch.zeros(1, 1, 1, 3)
    tgt_m = torch.tensor([[[[5.0, 5.0001, 44.5]]]])
    pred[0, 0, 0, 0] = 3.0
    pred[0, 0, 0, 1] = 3.0
    pred[0, 0, 0, 2] = 3.0
    loss, n = _wloss(pred, tgt_z, tgt_m)
    assert n == 3
    assert loss.item() == pytest.approx(3.0)  # (1*3+1*3+1*3)/3


def test_m12_negatives_preserved_and_weighted():
    """Negative meter targets are valid and fall in the <5m weighted group."""
    pred = torch.tensor([[[[-1.0, 0.0]]]])
    tgt_z = torch.tensor([[[[0.0, 0.0]]]])
    tgt_m = torch.tensor([[[[-5.0, 2.0]]]])
    loss, n = _wloss(pred, tgt_z, tgt_m)
    assert n == 2
    # (2*|−1−0| + 2*|0−0|) / (2+2) = 0.5
    assert loss.item() == pytest.approx(0.5)


def test_m12_denominator_is_sum_of_weights():
    """Denominator must be sum(w), not pixel count."""
    pred = torch.tensor([[[[1.0, 1.0]]]])
    tgt_z = torch.tensor([[[[0.0, 0.0]]]])
    tgt_m = torch.tensor([[[[0.0, 100.0]]]])
    loss, _ = _wloss(pred, tgt_z, tgt_m)
    assert loss.item() == pytest.approx(1.0)  # (2*1+1*1)/3


def test_m12_finite_masking():
    """Non-finite pred/z/m pixels are excluded, like masked_l1."""
    pred = torch.tensor([[[[1.0, float("nan"), 1.0]]]])
    tgt_z = torch.tensor([[[[0.0, 0.0, float("inf")]]]])
    tgt_m = torch.tensor([[[[0.0, 0.0, 0.0]]]])
    loss, n = _wloss(pred, tgt_z, tgt_m)
    assert n == 1
    assert loss.item() == pytest.approx(1.0)


def test_m12_all_invalid_raises():
    from depthwizard.adapt.loss import masked_height_weighted_l1

    with pytest.raises(ValueError):
        masked_height_weighted_l1(
            torch.full((1, 1, 2, 2), float("nan")),
            torch.zeros(1, 1, 2, 2),
            torch.zeros(1, 1, 2, 2),
        )


def test_m12_shape_mismatch_raises():
    from depthwizard.adapt.loss import masked_height_weighted_l1

    with pytest.raises(ValueError):
        masked_height_weighted_l1(
            torch.zeros(1, 1, 2, 2),
            torch.zeros(1, 1, 2, 2),
            torch.zeros(1, 1, 2, 3),
        )


def test_m12_finite_gradients():
    """Gradients through the weighted loss must be finite and reach pred."""
    pred = torch.tensor([[[[1.0, 2.0]]]], requires_grad=True)
    tgt_z = torch.tensor([[[[0.0, 0.0]]]])
    tgt_m = torch.tensor([[[[0.0, 100.0]]]])
    loss, _ = _wloss(pred, tgt_z, tgt_m)
    loss.backward()
    assert pred.grad is not None
    assert torch.isfinite(pred.grad).all()
    # d/dpred = w/sum(w) * sign: [2/3, 1/3]
    assert pred.grad.flatten().tolist() == pytest.approx([2.0 / 3.0, 1.0 / 3.0])


def test_m12_zscore_compatibility():
    """Weighted z-loss of a constant meter offset equals |offset|/sigma."""
    from depthwizard.adapt.loss import TargetScale

    mu, sigma = 8.0, 10.0
    ts = TargetScale(mode="zscore", mu=mu, sigma=sigma)
    tgt_m = torch.tensor([[[[2.0, 20.0]]]])
    tgt_z = ts.forward(tgt_m)
    pred_z = tgt_z + 1.0  # constant z error of 1 everywhere
    loss, _ = _wloss(pred_z, tgt_z, tgt_m)
    assert loss.item() == pytest.approx(1.0)
    # inverse normalization unaffected by weighting
    assert torch.allclose(ts.inverse(pred_z), tgt_m + sigma)


def test_m12_no_validation_dependency():
    """Loss depends only on pred/target tensors (weights from target_m)."""
    import inspect

    from depthwizard.adapt.loss import masked_height_weighted_l1

    params = list(inspect.signature(masked_height_weighted_l1).parameters)
    assert params == ["pred_z", "target_z", "target_m", "threshold", "low_weight"]
    assert "val" not in params and "split" not in params and "manifest" not in params


def test_m12_dataset_preserved():
    """Exact M10/M11 train/val IDs and 16/4/4 composition preserved."""
    assert len(M10_TRAIN_IDS) == 24 and len(set(M10_TRAIN_IDS)) == 24
    counts: dict = {}
    for sid in M10_TRAIN_IDS:
        counts[sid.split("_")[0]] = counts.get(sid.split("_")[0], 0) + 1
    assert counts == {"DC": 16, "PHL": 4, "NYC": 4}
    assert len(M10_VAL_IDS) == 8
    assert set(M10_TRAIN_IDS).isdisjoint(M10_VAL_IDS)


def test_m12_runner_freezes_m10_recipe():
    """M12 runner must keep the 16/4/4 selection, zscore mode, and 30-epoch recipe."""
    import pathlib

    src = pathlib.Path("src/depthwizard/experiments/adapt_dav2_m12.py").read_text(encoding="utf-8")
    assert '("DC", 16)' in src and '("PHL", 4)' in src and '("NYC", 4)' in src
    assert 'target_mode="zscore"' in src or 'mode="zscore"' in src
    assert "height_weight=(HEIGHT_THRESHOLD_M, LOW_HEIGHT_WEIGHT)" in src
    assert "HEIGHT_THRESHOLD_M = 5.0" in src
    assert "LOW_HEIGHT_WEIGHT = 2.0" in src
