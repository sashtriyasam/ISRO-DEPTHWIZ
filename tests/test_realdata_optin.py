"""Opt-in real-data integration test (skips cleanly without GAMUS_ROOT data).

Never downloads anything; only inspects a local root when it already exists.
Ordinary CI (no dataset) skips this module entirely.
"""

import os
from pathlib import Path

import pytest

pytest.importorskip("h5py")
pytest.importorskip("numpy")

from depthwizard.data.config import GamusConfig
from depthwizard.data.experiment import GamusExperimentDataset
from depthwizard.data.manifest import discover_records
from depthwizard.data.probe import probe_root
from depthwizard.data.schemas import GAMUS_VALID_LABELS
from depthwizard.data.validation import validate_records


def _resolve_probe_root() -> Path | None:
    env = os.environ.get("GAMUS_ROOT")
    candidates = [Path(env)] if env else []
    candidates.append(GamusConfig().resolve_root())
    for c in candidates:
        if c.exists() and (c / "images").exists():
            return c
    return None


PROBE_ROOT = _resolve_probe_root()
needs_real_data = pytest.mark.skipif(PROBE_ROOT is None, reason="GAMUS_ROOT with real data unavailable")


@needs_real_data
def test_real_manifest_probe_validates():
    recs = discover_records(PROBE_ROOT, splits=["train"])
    assert len(recs) > 0
    report = validate_records(recs, root=PROBE_ROOT, probe_arrays=False)
    assert report.ok, [str(e) for e in report.errors[:5]]


@needs_real_data
def test_real_probe_shapes_dtypes_keys():
    rep = probe_root(PROBE_ROOT, split="train")
    assert rep["n_samples"] > 0
    for s in rep["samples"]:
        img, hgt, lbl = (s["modalities"][m] for m in ("image", "height", "label"))
        assert img["shape"][0] == 1024 and img["shape"][2] == 3 and img["dtype"] == "uint8"
        assert img["h5_key"] == "image" and img["finite_pct"] == 100.0
        assert hgt["shape"] == [1024, 1024] and hgt["dtype"] == "float32" and hgt["h5_key"] == "image"
        assert hgt["finite_pct"] > 99.0
        assert lbl["shape"] == [1024, 1024] and lbl["h5_key"] == "image"
        assert not lbl["classes"]["invalid_values"]
        assert s["aligned"] is True


@needs_real_data
def test_real_experiment_tensors():
    recs = discover_records(PROBE_ROOT, splits=["train"])[:2]
    ds = GamusExperimentDataset(records=recs, root=PROBE_ROOT)
    item = ds[0]
    assert tuple(item["image"].shape[1:]) == (1024, 1024) and item["image"].shape[0] == 3
    assert tuple(item["height"].shape[1:]) == (1024, 1024) and item["height"].shape[0] == 1
    assert tuple(item["label"].shape) == (1024, 1024)
    import numpy as _np

    assert set(int(v) for v in _np.unique(item["label"])) <= set(GAMUS_VALID_LABELS)
