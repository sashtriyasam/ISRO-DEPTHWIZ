"""Experiment-runner tests (mock backend; deterministic manifest fixtures)."""

import json
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
h5py = pytest.importorskip("h5py")

from depthwizard.depth.base import DepthResult  # noqa: E402
from depthwizard.experiments.depth_anything_v2 import run_experiment, select_records  # noqa: E402


def _write_h5(path: Path, arr) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(str(path), "w") as f:
        f.create_dataset("image", data=arr)


def _root(tmp: Path, sid: str, seed: int = 0, h: int = 16, w: int = 12):
    rng = np.random.default_rng(seed)
    _write_h5(tmp / f"images/train/{sid}_RGB.h5", rng.integers(0, 256, (h, w, 3)).astype(np.uint8))
    _write_h5(tmp / f"heights/train/{sid}_AGL.h5", rng.uniform(0, 30, (h, w)).astype(np.float32))
    _write_h5(tmp / f"classes/train/{sid}_CLS.h5", rng.integers(0, 7, (h, w)).astype(np.float32))
    return tmp


class _MockBackend:
    name = "mock-dav2"

    def __init__(self):
        self.calls = 0

    def load(self):
        return None

    def config_dict(self):
        return {"backend": self.name, "scale": "relative"}

    def infer(self, image_rgb):
        self.calls += 1
        h, w = image_rgb.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
        pred = (xx - yy) / (h + w)
        return DepthResult(prediction=pred, scale_semantics="relative", is_metric=False, model_name="mock")


def _manifest(tmp: Path, sids: list[str]) -> Path:
    from depthwizard.data.manifest import build_manifest

    mp = tmp / "m.json"
    build_manifest(tmp, output_path=mp)
    return mp


def test_select_records_deterministic_and_filtered(tmp_path):
    _root(tmp_path, "DC_02_24", seed=1)
    _root(tmp_path, "DC_01_25", seed=2)
    mp = _manifest(tmp_path, ["DC_01_25", "DC_02_24"])
    recs = select_records(mp, "train")
    assert [r.sample_id for r in recs] == ["DC_01_25", "DC_02_24"]
    only = select_records(mp, "train", sample_ids=["DC_02_24"])
    assert [r.sample_id for r in only] == ["DC_02_24"]
    capped = select_records(mp, "train", max_samples=1)
    assert len(capped) == 1
    assert select_records(mp, "val") == []


def test_run_experiment_mock_end_to_end(tmp_path, monkeypatch):
    _root(tmp_path, "DC_01_25", seed=3)
    _root(tmp_path, "DC_02_24", seed=4)
    mp = _manifest(tmp_path, ["DC_01_25"])
    out = tmp_path / "exp"
    monkeypatch.chdir(tmp_path)  # adapter root default data/gamus irrelevant; pass root explicitly
    be = _MockBackend()
    res = run_experiment(manifest=mp, output=out, split="train", root=tmp_path, backend=be)
    assert res["n_samples"] == 2 and be.calls == 2
    assert (out / "config.json").is_file() and (out / "results.json").is_file() and (out / "README.md").is_file()
    assert res["evaluation"]["protocol"].startswith("per-image-affine")
    assert res["dataset"]["target_semantics"].startswith("nDSM/AGL")
    assert res["bring_up"] is True  # <=3 samples labeled bring-up
    assert all("aligned_mae" in s for s in res["per_sample"])
    # Reproducibility metadata present.
    assert res["dataset"]["sample_ids"] == ["DC_01_25", "DC_02_24"]
    assert res["software"]["python"]
    # No raw relative-vs-meter MAE anywhere.
    assert "raw_mae" not in json.dumps(res)


def test_run_experiment_empty_selection_raises(tmp_path):
    _root(tmp_path, "DC_01_25")
    mp = _manifest(tmp_path, ["DC_01_25"])
    with pytest.raises(ValueError, match="No records selected"):
        run_experiment(manifest=mp, output=tmp_path / "x", split="val", root=tmp_path, backend=_MockBackend())


def test_run_experiment_missing_rgb_raises(tmp_path):
    _root(tmp_path, "DC_01_25")
    mp = _manifest(tmp_path, ["DC_01_25"])
    (tmp_path / "images/train/DC_01_25_RGB.h5").unlink()  # remove AFTER manifest build
    with pytest.raises(FileNotFoundError, match="Missing RGB"):
        run_experiment(manifest=mp, output=tmp_path / "x", split="train", root=tmp_path, backend=_MockBackend())
