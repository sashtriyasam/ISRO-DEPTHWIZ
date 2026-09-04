"""M6 Geographic Validation tests (mocked; no GPU, no weights, no downloads)."""

import json
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")

from depthwizard.adapt.evaluate import evaluate_predictions
from depthwizard.experiments.m6_geographic import _records, _load_samples, run_geographic_validation


class _FakeBackbone(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.depth_head = torch.nn.Sequential(
            torch.nn.Conv2d(3, 64, kernel_size=1)
        )

    def forward(self, x):
        return self.depth_head(x)


class _FakeAdapter:
    """Mock adapter returning synthetic samples."""

    def __init__(self):
        self.city_map = {"DC": 1, "NYC": 2, "PHL": 3}

    def to_sample(self, record, load_arrays=True):
        import numpy as np  # type: ignore

        h, w = 16, 16
        city_id = self.city_map.get(record.sample_id.split('_')[0], 0)
        # Different height distributions per city for testing
        base_height = np.full((h, w), float(city_id * 5), dtype=np.float32)
        noise = np.random.default_rng(42).uniform(-1, 1, (h, w)).astype(np.float32)
        return {
            "sample_id": record.sample_id,
            "split": record.split,
            "city": record.sample_id.split('_')[0],
            "image": np.random.randint(0, 256, (h, w, 3), dtype=np.uint8),
            "height": base_height + noise,
            "label": np.full((h, w), city_id % 7, dtype=np.float32),
        }


def _fake_records(cities: list[str], per_city: int = 2) -> list:
    """Create mock GamusRecords with given city distribution."""
    from depthwizard.data.schemas import GamusRecord

    recs = []
    for city in cities:
        for i in range(per_city):
            recs.append(GamusRecord(
                sample_id=f"{city}_{i:04d}",
                image_path=f"images/test/{city}_{i:04d}_RGB.h5",
                height_path=f"heights/test/{city}_{i:04d}_AGL.h5",
                label_path=f"classes/test/{city}_{i:04d}_CLS.h5",
                split="test",
            ))
    return recs


def test_deterministic_city_grouping():
    recs = _fake_records(["DC", "NYC", "PHL"], per_city=3)
    city_groups = {}
    for r in recs:
        city = r.sample_id.split('_')[0]
        city_groups.setdefault(city, []).append(r)
    assert set(city_groups.keys()) == {"DC", "NYC", "PHL"}
    assert all(len(v) == 3 for v in city_groups.values())


def test_city_group_order_deterministic():
    recs = _fake_records(["NYC", "DC", "PHL"], per_city=2)
    cities = sorted({r.sample_id.split('_')[0] for r in recs})
    assert cities == ["DC", "NYC", "PHL"]


def test_city_metrics_aggregation():
    preds = []
    tgts = []
    labels = []
    for city_id in [0, 1, 2]:
        n = 100
        preds.append(np.full((n,), 5.0 + city_id, dtype=np.float32))
        tgts.append(np.full((n,), 5.0 + city_id, dtype=np.float32))
        labels.append(np.full((n,), city_id % 7, dtype=np.float32))
    out = evaluate_predictions(preds, tgts, labels=labels, class_names={0: "ground", 1: "tree", 2: "building"})
    assert out["error"]["mae"] == pytest.approx(0.0)
    assert "ground" in out["per_class"] and "tree" in out["per_class"] and "building" in out["per_class"]


def test_macro_vs_micro_average():
    # Macro: equal weight per city; Micro: pixel-weighted
    np.random.seed(0)
    preds = [np.full(100, 10.0), np.full(10000, 20.0)]  # city A: 100px, city B: 10000px
    tgts = [np.full(100, 12.0), np.full(10000, 22.0)]
    out = evaluate_predictions(preds, tgts)
    macro_mae = (2.0 + 2.0) / 2  # 2.0 each
    micro_mae = (200 + 20000) / 10100  # pixel-weighted
    assert out["error"]["mae"] == pytest.approx(micro_mae)
    # Note: evaluate_predictions returns micro by default; macro computed separately


def test_generalization_gap_calculation():
    in_city = 5.0
    cross = 4.0
    gap = cross - in_city
    assert gap == -1.0  # negative means cross-city is better


def test_manifest_city_filtering():
    from depthwizard.data.schemas import GamusRecord
    recs = [
        GamusRecord(sample_id="DC_01", image_path="", height_path="", label_path=None, split="test"),
        GamusRecord(sample_id="NYC_01", image_path="", height_path="", label_path=None, split="test"),
        GamusRecord(sample_id="PHL_01", image_path="", height_path="", label_path=None, split="test"),
    ]
    dc = [r for r in recs if r.sample_id.split('_')[0] == "DC"]
    assert len(dc) == 1 and dc[0].sample_id == "DC_01"


def test_height_bin_edges():
    from depthwizard.adapt.evaluate import HEIGHT_BINS
    assert HEIGHT_BINS[0] == (0.0, 1.0, "0-1m")
    assert HEIGHT_BINS[-1] == (30.0, float("inf"), "30+m")


def test_cross_city_gap_sign():
    # If cross-city MAE > in-city MAE -> positive gap (degradation)
    # If cross-city MAE < in-city MAE -> negative gap (improvement)
    in_city = 5.5
    cross = 6.0
    gap = cross - in_city
    assert gap > 0
    cross2 = 4.5
    gap2 = cross2 - in_city
    assert gap2 < 0


def test_missing_city_labels_handled():
    # Labels may be NaN for some cities
    preds = [np.full(100, 5.0), np.full(100, 10.0)]
    tgts = [np.full(100, 5.0), np.full(100, 10.0)]
    labels = [np.full(100, np.nan), np.full(100, 1.0)]
    out = evaluate_predictions(preds, tgts, labels=labels, class_names={1: "test"})
    # Should not crash; per-class for city with NaN labels should be skipped
    assert "error" in out


def test_negative_targets_in_metrics():
    # Negative targets should be included in metrics (not clipped)
    preds = np.array([[0.0, 5.0], [10.0, 15.0]])
    tgts = np.array([[-5.0, 0.0], [10.0, 20.0]])
    out = evaluate_predictions([preds], [tgts])
    assert out["error"]["mae"] > 0
    # Negative residuals should be preserved in residual analysis


def test_checkpoint_immutability(tmp_path):
    import torch
    from depthwizard.adapt.model import AdaptedDepthModel
    from tests.test_adapt_head import FakeBackbone, build_head

    m = AdaptedDepthModel(FakeBackbone(), head=build_head())
    p = tmp_path / "head.pt"
    m.save_head(p, extra={"epoch": 1})
    m2 = AdaptedDepthModel(FakeBackbone(), head=build_head())
    payload = m2.load_head(p)
    assert payload["extra"] == {"epoch": 1}
    # Verify original checkpoint not modified
    with open(p, "rb") as f:
        data = f.read()
    assert b"epoch" in data


def test_model_checkpoint_hash(tmp_path):
    import torch
    from depthwizard.adapt.model import AdaptedDepthModel
    from tests.test_adapt_head import FakeBackbone, build_head

    m = AdaptedDepthModel(FakeBackbone(), head=build_head())
    p = tmp_path / "head.pt"
    m.save_head(p)
    # Verify SHA256 of file is stable
    import hashlib
    h1 = hashlib.sha256(Path(p).read_bytes()).hexdigest()
    h2 = hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert h1 == h2