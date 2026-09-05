"""Tests for M16 controlled GeoNRW adaptation (mocked; no GPU, no weights, no downloads)."""

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")


def _items():
    """Fixture triplet items across fake cities (no real data)."""
    items = []
    for city, n in [("bochum", 8), ("coesfeld", 8), ("herford", 8), ("paderborn", 8)]:
        for i in range(n):
            stem = f"{i:03d}_0000"
            items.append({"city": city, "stem": stem,
                          "rgb": f"{city}/{stem}_rgb.jp2", "dem": f"{city}/{stem}_dem.tif"})
    return items


def test_m16_split_deterministic_composition():
    from depthwizard.experiments.m16_geonrw_adapt import select_split

    s = select_split(_items(), train_cities=["bochum", "coesfeld"],
                     val_cities=["herford", "paderborn"], n_per_city=6,
                     held_out=["duesseldorf", "herne", "neuss"])
    assert len(s["train"]) == 12 and len(s["val"]) == 12
    assert [t["stem"] for t in s["train"][:6]] == [f"{i:03d}_0000" for i in range(6)]
    assert {t["city"] for t in s["train"]} == {"bochum", "coesfeld"}
    assert {t["city"] for t in s["val"]} == {"herford", "paderborn"}


def test_m16_no_train_val_overlap():
    from depthwizard.experiments.m16_geonrw_adapt import select_split

    s = select_split(_items(), train_cities=["bochum"], val_cities=["herford"],
                     n_per_city=4, held_out=["neuss"])
    tids = {t["city"] + "/" + t["stem"] for t in s["train"]}
    vids = {t["city"] + "/" + t["stem"] for t in s["val"]}
    assert tids.isdisjoint(vids)


def test_m16_held_out_presence_raises():
    from depthwizard.experiments.m16_geonrw_adapt import select_split

    items = _items() + [{"city": "neuss", "stem": "000_0000",
                         "rgb": "x", "dem": "y"}]
    with pytest.raises(ValueError, match="Held-out"):
        select_split(items, train_cities=["bochum"], val_cities=["herford"],
                     n_per_city=4, held_out=["neuss"])


def test_m16_train_val_city_overlap_raises():
    from depthwizard.experiments.m16_geonrw_adapt import select_split

    with pytest.raises(ValueError, match="overlap"):
        select_split(_items(), train_cities=["bochum"], val_cities=["bochum"],
                     n_per_city=4, held_out=["neuss"])


def test_m16_short_city_raises():
    from depthwizard.experiments.m16_geonrw_adapt import select_split

    with pytest.raises(ValueError, match="only"):
        select_split(_items(), train_cities=["bochum"], val_cities=["herford"],
                     n_per_city=99, held_out=["neuss"])


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


def _tiny_model(seed=0):
    from depthwizard.adapt.head import build_head
    from depthwizard.adapt.model import AdaptedDepthModel

    torch.manual_seed(seed)
    return AdaptedDepthModel(_FakeBackbone(), head=build_head())


def _tiny_samples(n=2, hw=16, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        out.append({
            "sample_id": f"s{i}",
            "image": rng.integers(0, 256, (hw, hw, 3)).astype(np.uint8),
            "height": (rng.normal(100.0, 10.0, (hw, hw))).astype(np.float32),
        })
    return out


def test_m16_selection_max_picks_max_pearson(tmp_path):
    """selection_mode='max' must select the max (not min) val Pearson epoch."""
    from depthwizard.adapt.train import train_adapted_model
    from depthwizard.adapt.loss import TargetScale

    m = _tiny_model()
    tr, va = _tiny_samples(2), _tiny_samples(2, seed=1)
    s = train_adapted_model(
        m, tr, va, tmp_path / "max", epochs=3, lr=1e-3, seed=0,
        selection_metric="pearson", selection_mode="max",
        out_hw=(16, 16), target_scale=TargetScale(mode="raw"),
    )
    pears = [h["val_pearson"] for h in s["history"] if h["val_pearson"] is not None]
    assert pears, "expected logged pearson values"
    assert s["best_epoch"] == int(np.argmax(pears))
    assert s["best_value"] == pytest.approx(max(pears))
    assert s["selection_mode"] == "max"


def test_m16_selection_min_default_unchanged(tmp_path):
    """Default selection_mode='min' preserves legacy MAE behavior."""
    from depthwizard.adapt.train import train_adapted_model
    from depthwizard.adapt.loss import TargetScale

    m = _tiny_model()
    tr, va = _tiny_samples(2), _tiny_samples(2, seed=1)
    s = train_adapted_model(
        m, tr, va, tmp_path / "min", epochs=3, lr=1e-3, seed=0,
        out_hw=(16, 16), target_scale=TargetScale(mode="raw"),
    )
    maes = [h["val_mae"] for h in s["history"]]
    assert s["best_epoch"] == int(np.argmin(maes))
    assert s["selection_mode"] == "min"


def test_m16_explicit_zscore_stats_preserved(tmp_path):
    """Explicit mu/sigma must NOT be recomputed from train data."""
    from depthwizard.adapt.train import train_adapted_model
    from depthwizard.adapt.loss import TargetScale

    m = _tiny_model()
    tr, va = _tiny_samples(2), _tiny_samples(2, seed=1)
    s = train_adapted_model(
        m, tr, va, tmp_path / "zs", epochs=1, lr=1e-3, seed=0,
        out_hw=(16, 16),
        target_scale=TargetScale(mode="zscore", mu=8.037330237035235, sigma=10.304011604437477),
    )
    assert s["target_scale"]["mu"] == pytest.approx(8.037330237035235)
    assert s["target_scale"]["sigma"] == pytest.approx(10.304011604437477)


def test_m16_head_init_roundtrip(tmp_path):
    """M10-style head checkpoint must load into a fresh head (init path)."""
    m1, m2 = _tiny_model(seed=0), _tiny_model(seed=1)
    p = m1.save_head(tmp_path / "h.pt", extra={"epoch": 22})
    payload = m2.load_head(p)
    for k in m1.head.state_dict():
        assert torch.equal(m1.head.state_dict()[k], m2.head.state_dict()[k])
    assert payload["extra"] == {"epoch": 22}
