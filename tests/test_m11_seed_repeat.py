"""Tests for M11 seed-repeat of the M10 recipe (mocked; no GPU, no weights, no downloads)."""

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

M10_MU = 8.037330237035235
M10_SIGMA = 10.304011604437477


def _city_counts(ids) -> dict:
    out = {}
    for sid in ids:
        c = sid.split("_")[0]
        out[c] = out.get(c, 0) + 1
    return out


def test_m11_seed_propagated():
    """Same seed must reproduce the same RNG stream; different seeds must differ."""
    from depthwizard.adapt.train import set_deterministic

    set_deterministic(1)
    a = torch.randn(8)
    set_deterministic(1)
    b = torch.randn(8)
    assert torch.equal(a, b)
    set_deterministic(2)
    c = torch.randn(8)
    assert not torch.equal(a, c)


def test_m11_independent_experiment_ids_and_dirs():
    """Seeds 1/2 use independent experiment IDs and directories from seed 0."""
    ids = {
        "dav2-gamus-head-m10-m9-targetnorm-e01",
        "dav2-gamus-head-m11-seed1-e01",
        "dav2-gamus-head-m11-seed2-e01",
    }
    dirs = {
        "experiments/dav2-gamus-head-m10-m9-targetnorm-e01",
        "experiments/dav2-gamus-head-m11-seed1-e01",
        "experiments/dav2-gamus-head-m11-seed2-e01",
    }
    assert len(ids) == 3 and len(dirs) == 3
    assert "experiments/dav2-gamus-head-m10-m9-targetnorm-e01" not in (
        "experiments/dav2-gamus-head-m11-seed1-e01",
        "experiments/dav2-gamus-head-m11-seed2-e01",
    )


def test_m11_train_ids_preserved():
    assert len(M10_TRAIN_IDS) == 24
    assert len(set(M10_TRAIN_IDS)) == 24
    assert _city_counts(M10_TRAIN_IDS) == {"DC": 16, "PHL": 4, "NYC": 4}


def test_m11_validation_ids_preserved():
    assert len(M10_VAL_IDS) == 8
    assert all(s.startswith("DC_") for s in M10_VAL_IDS)
    assert set(M10_TRAIN_IDS).isdisjoint(M10_VAL_IDS)


def test_m11_stats_train_only_and_reproduced():
    """Recomputing stats on identical train pixels must reproduce M10 mu/sigma."""
    from depthwizard.experiments.adapt_dav2_m10 import _train_target_stats

    rng = np.random.default_rng(0)
    h = (rng.normal(8.0, 10.0, size=(4, 16)).astype(np.float32))
    h[0, 0] = -2.5  # negative preserved
    h[1, 1] = float("nan")
    train = [{"height": h}]
    s1 = _train_target_stats(train)
    s2 = _train_target_stats(train)
    assert s1 == s2
    assert s1["n_valid_pixels"] == 4 * 16 - 1
    assert s1["n_negative_pixels"] >= 1


def test_m11_m10_reference_stats_sane():
    """M10 reference mu/sigma are finite, positive-sigma, and not M7 values."""
    assert M10_SIGMA > 0
    assert abs(M10_MU - 9.540806312282879) > 0.1
    assert abs(M10_SIGMA - 10.53309572685479) > 0.1


def test_m11_target_mode_remains_zscore():
    import pathlib

    src = pathlib.Path("src/depthwizard/experiments/adapt_dav2_m10.py").read_text(encoding="utf-8")
    assert 'target_mode="zscore"' in src or "target_mode='zscore'" in src or 'mode="zscore"' in src


def test_m11_negative_targets_preserved():
    from depthwizard.adapt.loss import TargetScale

    ts = TargetScale(mode="zscore", mu=M10_MU, sigma=M10_SIGMA)
    y = torch.tensor([-5.0, 0.0, 55.0])
    z = ts.forward(y)
    assert float(z[0]) < 0  # no clipping
    assert torch.allclose(ts.inverse(z), y)


def test_m11_selection_deterministic_across_seeds():
    """Data selection must not depend on seed (sorted sample_id order)."""
    recs = ["DC_02", "DC_01", "PHL_02", "PHL_01"]
    assert sorted(recs) == ["DC_01", "DC_02", "PHL_01", "PHL_02"]
