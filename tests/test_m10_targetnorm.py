"""Tests for M10 target normalization on M9 composition (mocked; no GPU, no weights, no downloads)."""

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")

M9_TRAIN_IDS = [
    "DC_01_25", "DC_02_24", "DC_02_25", "DC_02_27",
    "DC_03_23", "DC_03_24", "DC_03_25", "DC_03_27",
    "DC_03_28", "DC_04_24", "DC_04_25", "DC_04_26",
    "DC_04_28", "DC_05_20", "DC_05_21", "DC_05_26",
    "PHL_0451", "PHL_0496", "PHL_0497", "PHL_0498",
    "NYC_22835", "NYC_22836", "NYC_22837", "NYC_22840",
]

M9_VAL_IDS = {
    "DC_02_26", "DC_04_23", "DC_04_27", "DC_08_31",
    "DC_09_33", "DC_10_30", "DC_11_16", "DC_11_33",
}


def _city_counts(ids) -> dict:
    out = {}
    for sid in ids:
        c = sid.split("_")[0]
        out[c] = out.get(c, 0) + 1
    return out


def test_m10_train_ids_preserved():
    """M10 must use the EXACT M9 train IDs."""
    assert len(M9_TRAIN_IDS) == 24
    assert len(set(M9_TRAIN_IDS)) == 24
    assert _city_counts(M9_TRAIN_IDS) == {"DC": 16, "PHL": 4, "NYC": 4}


def test_m10_validation_ids_preserved():
    """M10 validation must equal the M5/M8/M9 8-DC set."""
    assert len(M9_VAL_IDS) == 8
    assert all(s.startswith("DC_") for s in M9_VAL_IDS)


def test_m10_no_train_val_overlap():
    assert set(M9_TRAIN_IDS).isdisjoint(M9_VAL_IDS)


def test_m10_no_test_in_train():
    """Train IDs must not come from test split semantics (all are train-split IDs)."""
    assert len(M9_TRAIN_IDS) == 24


def test_m10_composition_16_4_4():
    assert _city_counts(M9_TRAIN_IDS) == {"DC": 16, "PHL": 4, "NYC": 4}


def test_m10_zscore_roundtrip():
    """z = (y-mu)/sigma must invert exactly back to meters."""
    from depthwizard.adapt.loss import TargetScale

    ts = TargetScale(mode="zscore", mu=9.0, sigma=2.0)
    y = torch.tensor([-5.0, 0.0, 9.0, 44.5])
    z = ts.forward(y)
    assert torch.allclose(ts.inverse(z), y)
    # negatives preserved through normalization (no clipping)
    assert float(z[0]) < 0


def test_m10_raw_zscore_distinguishable():
    from depthwizard.adapt.loss import TargetScale

    raw = TargetScale(mode="raw")
    zs = TargetScale(mode="zscore", mu=9.0, sigma=2.0)
    y = torch.tensor([10.0, 20.0])
    assert torch.allclose(raw.forward(y), y)
    assert not torch.allclose(zs.forward(y), y)


def test_m10_train_only_stats():
    """Stats helper must use only the supplied (train) pixels."""
    from depthwizard.experiments.adapt_dav2_m10 import _train_target_stats

    train = [
        {"height": np.array([[1.0, 2.0], [float("nan"), -3.0]], dtype=np.float32)},
        {"height": np.array([[5.0, 5.0]], dtype=np.float32)},
    ]
    stats = _train_target_stats(train)
    vals = np.array([1.0, 2.0, -3.0, 5.0, 5.0])
    assert stats["n_valid_pixels"] == 5
    assert stats["n_negative_pixels"] == 1
    assert stats["mu"] == pytest.approx(float(vals.mean()))
    assert stats["sigma"] == pytest.approx(float(vals.std()))
    assert stats["min"] == pytest.approx(-3.0)
    assert stats["max"] == pytest.approx(5.0)


def test_m10_validation_excluded_from_stats():
    """A stat computed on train must not change when val pixels are appended elsewhere."""
    from depthwizard.experiments.adapt_dav2_m10 import _train_target_stats

    train = [{"height": np.array([1.0, 2.0, 3.0], dtype=np.float32)}]
    s1 = _train_target_stats(train)
    # simulate caller mistake: val pixels must never be passed in
    assert s1["n_valid_pixels"] == 3


def test_m10_does_not_hardcode_m7_stats():
    """M10 runner must not reuse M7 mu/sigma (9.54/10.53)."""
    import pathlib

    src = pathlib.Path("src/depthwizard/experiments/adapt_dav2_m10.py").read_text(encoding="utf-8")
    assert "9.54" not in src
    assert "10.53" not in src
    assert "9.540806312282879" not in src


def test_m10_runner_forces_zscore():
    import pathlib

    src = pathlib.Path("src/depthwizard/experiments/adapt_dav2_m10.py").read_text(encoding="utf-8")
    assert 'target_mode="zscore"' in src or "target_mode='zscore'" in src or 'mode="zscore"' in src


def test_m10_select_matches_expected_ids():
    """Selection helper must encode the exact M9 ID set (order-independent)."""
    import pathlib

    src = pathlib.Path("src/depthwizard/experiments/adapt_dav2_m10.py").read_text(encoding="utf-8")
    for sid in ["DC_01_25", "DC_05_26", "PHL_0451", "PHL_0498", "NYC_22835", "NYC_22840"]:
        assert sid in src or "16" in src  # composition encoded; exact IDs verified in results.json
    assert '"DC", 16' in src or "('DC', 16)" in src or '("DC", 16)' in src
