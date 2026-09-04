"""M5 single-factor controls (no GPU, no weights, no downloads).

Verifies the M4->M5 comparison is a clean epochs-only extension:
fresh initialization, frozen backbone, val-based selection, disjoint splits,
no test usage, reproducibility metadata, and M4 artifact immutability.
"""

import json
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")

from tests.test_adapt_head import FakeBackbone, _rgb  # noqa: E402

from depthwizard.adapt.head import build_head  # noqa: E402
from depthwizard.adapt.model import AdaptedDepthModel  # noqa: E402
from depthwizard.adapt.train import train_adapted_model  # noqa: E402

M4_BEST_VAL_MAE = 5.491432826047782
M4_EPOCHS = 15
M5_EPOCHS = 30


def _fresh_model(seed=0):
    torch.manual_seed(seed)
    return AdaptedDepthModel(FakeBackbone(), head=build_head())


def _tiny(n=2, h=16, seed=0):
    rng = np.random.default_rng(seed)
    return [
        {
            "image": rng.integers(0, 256, (h, h, 3)).astype(np.uint8),
            "height": rng.uniform(0, 10, (h, h)).astype(np.float32),
        }
        for _ in range(n)
    ]


# 1. Epoch configuration respected.
def test_epoch_budget_respected(tmp_path):
    m = _fresh_model()
    tiny = _tiny()
    s = train_adapted_model(m, tiny, tiny, tmp_path, epochs=3, seed=0, out_hw=(16, 16))
    assert s["epochs"] == 3 and len(s["history"]) == 3
    assert [r["epoch"] for r in s["history"]] == [0, 1, 2]


# 2/4. Fresh init from same seed; M4 checkpoint never loaded.
def test_fresh_init_deterministic_not_resumed(tmp_path):
    a, b = _fresh_model(seed=0), _fresh_model(seed=0)
    for pa, pb in zip(a.head.parameters(), b.head.parameters()):
        assert torch.equal(pa, pb)
    ckpt = Path("experiments/dav2-gamus-head-m4-e01/checkpoints/best.pt")
    if not ckpt.is_file():
        pytest.skip("M4 best checkpoint absent (git-ignored)")
    payload = torch.load(str(ckpt), map_location="cpu", weights_only=False)
    disk = payload["head_state"]
    live = a.head.state_dict()
    assert set(disk) == set(live)
    assert any(not torch.equal(disk[k], live[k]) for k in disk), "fresh init must differ from M4 best"


# 5/6. Backbone frozen; only head receives gradients.
def test_backbone_frozen_only_head_grads():
    m = _fresh_model()
    m.assert_frozen()
    assert all(not p.requires_grad for p in m.backbone.parameters())
    opt = torch.optim.SGD([p for p in m.head.parameters() if p.requires_grad], lr=1e-3)
    opt.zero_grad()
    from depthwizard.adapt.loss import masked_l1

    pred = m.forward(_rgb(16, 16), out_hw=(16, 16)).unsqueeze(0)
    loss, _ = masked_l1(pred, torch.zeros_like(pred))
    loss.backward()
    assert all(p.grad is None for p in m.backbone.parameters())
    assert any(p.grad is not None for p in m.head.parameters() if p.requires_grad)


# 7/8. Best-val-MAE selection recorded in the final report.
def test_best_val_selection_recorded(tmp_path):
    m = _fresh_model()
    tiny = _tiny()
    s = train_adapted_model(m, tiny, tiny, tmp_path, epochs=2, seed=0, out_hw=(16, 16))
    rep = json.loads((tmp_path / "train_summary.json").read_text(encoding="utf-8"))
    assert rep["best_epoch"] == s["best_epoch"]
    assert rep["best_value"] == min(r["val_mae"] for r in rep["history"])


# 9/10. Train/val disjoint; test never selected.
def test_split_discipline_on_m4_manifest():
    from depthwizard.experiments.adapt_dav2 import _records

    mp = Path("manifests/gamus.m4.manifest.json")
    if not mp.is_file():
        pytest.skip("m4 manifest absent")
    train = {r.sample_id for r in _records(mp, "train")}
    val = {r.sample_id for r in _records(mp, "val")}
    test = _records(mp, "test")
    assert train and val and not (train & val)
    assert test == []


# 11. M5 results carry full reproducibility metadata.
def test_m5_results_metadata():
    p = Path("experiments/dav2-gamus-head-m5-e01/results.json")
    if not p.is_file():
        pytest.skip("M5 results absent")
    r = json.loads(p.read_text(encoding="utf-8"))
    assert r["experiment_id"] == "dav2-gamus-head-m5-e01"
    assert r["training"]["epochs"] == M5_EPOCHS and r["training"]["seed"] == 0
    assert r["training"]["lr"] == 1e-3 and r["training"]["optimizer"] == "Adam"
    assert r["dataset"]["test_used"] is False
    assert len(r["dataset"]["train_ids"]) == 24 and len(r["dataset"]["val_ids"]) == 8
    assert r["model"]["trainable"] == 23201 and r["software"]["python"]
    assert "not" in r["m3_reference_same_val"]["note"].lower() and "apples" in r["m3_reference_same_val"]["note"].lower()


# 12. M4 artifacts immutable (config + best value pinned).
def test_m4_artifacts_untouched():
    cfg = Path("experiments/dav2-gamus-head-m4-e01/config.json")
    res = Path("experiments/dav2-gamus-head-m4-e01/results.json")
    if not cfg.is_file() or not res.is_file():
        pytest.skip("M4 artifacts absent")
    assert json.loads(cfg.read_text(encoding="utf-8"))["epochs"] == M4_EPOCHS
    assert json.loads(res.read_text(encoding="utf-8"))["training"]["best_value"] == pytest.approx(M4_BEST_VAL_MAE)
