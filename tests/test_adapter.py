import tempfile
from pathlib import Path

import pytest

from depthwizard.data.adapter import GamusAdapter
from depthwizard.data.config import GamusConfig
from depthwizard.data.manifest import build_manifest
from depthwizard.data.schemas import GamusRecord, GamusSample


def _make_root_with_samples(tmp: Path, split="train", ids=None):
    ids = ids or ["DC_01_25", "DC_03_26"]
    for sid in ids:
        (tmp / "images" / split).mkdir(parents=True, exist_ok=True)
        (tmp / "heights" / split).mkdir(parents=True, exist_ok=True)
        (tmp / "classes" / split).mkdir(parents=True, exist_ok=True)
        (tmp / "images" / split / f"{sid}_RGB.h5").write_bytes(b"")
        (tmp / "heights" / split / f"{sid}_AGL.h5").write_bytes(b"")
        (tmp / "classes" / split / f"{sid}_CLS.h5").write_bytes(b"")


def test_adapter_sample_contract():
    # Use in-memory records, not filesystem, to test contract without dataset
    tmp = Path(tempfile.mkdtemp())
    cfg = GamusConfig(root=tmp)
    adapter = GamusAdapter(config=cfg)
    rec = GamusRecord(
        sample_id="DC_03_26",
        image_path="images/train/DC_03_26_RGB.h5",
        height_path="heights/train/DC_03_26_AGL.h5",
        label_path="classes/train/DC_03_26_CLS.h5",
        split="train",
        source="gamus",
    )
    sample = adapter.to_sample(rec, load_arrays=False)
    assert isinstance(sample, GamusSample)
    assert sample.sample_id == "DC_03_26"
    assert sample.split == "train"
    assert sample.source == "gamus"
    assert sample.image_path == tmp / "images/train/DC_03_26_RGB.h5"
    assert sample.height_path == tmp / "heights/train/DC_03_26_AGL.h5"
    assert sample.label_path == tmp / "classes/train/DC_03_26_CLS.h5"
    # Arrays not loaded without dataset
    assert sample.image is None
    assert sample.height is None
    assert sample.label is None
    # Metadata preserves provenance and makes semantics explicit
    assert sample.metadata["provenance"] == "gamus"
    # Explicit that RGB=input, height=nDSM ground truth, label=semantic not depth
    # Check that adapter does not confuse height as elevation prediction
    assert "AGL" in sample.height_path.name
    assert "heights" in sample.height_path.as_posix()


def test_adapter_available_false_when_no_dataset():
    tmp = Path(tempfile.mkdtemp()) / "empty_root_no_images"
    tmp.mkdir(parents=True, exist_ok=True)
    adapter = GamusAdapter(root=tmp)
    assert adapter.available() is False
    # list_records should return empty without error
    assert adapter.list_records() == []
    assert len(adapter) == 0
    # to_sample still works (lazy) even though files missing — no exception
    rec = GamusRecord(
        sample_id="DC_01_25",
        image_path="images/train/DC_01_25_RGB.h5",
        height_path="heights/train/DC_01_25_AGL.h5",
        label_path="classes/train/DC_01_25_CLS.h5",
        split="train",
    )
    sample = adapter.to_sample(rec, load_arrays=True)
    # Files missing => arrays remain None, but contract still holds
    assert sample.sample_id == "DC_01_25"
    assert sample.image is None


def test_adapter_with_real_filesystem_listing(tmp_path):
    root = tmp_path / "gamus"
    _make_root_with_samples(root, ids=["DC_01_25", "DC_03_26"])
    adapter = GamusAdapter(root=root)
    assert adapter.available() is True
    recs = adapter.list_records(split="train")
    assert len(recs) == 2
    assert sorted([r.sample_id for r in recs]) == ["DC_01_25", "DC_03_26"]
    # iter_samples yields GamusSample per record
    samples = list(adapter.iter_samples(split="train", load_arrays=False))
    assert len(samples) == 2
    # Ensure deterministic order
    assert [s.sample_id for s in samples] == sorted([s.sample_id for s in samples])


def test_adapter_via_manifest_without_filesystem(tmp_path):
    # Build a manifest from one root, then use adapter with different root but manifest path
    root = tmp_path / "root1"
    _make_root_with_samples(root, ids=["DC_10_20"])
    manifest_path = tmp_path / "manifest.json"
    build_manifest(root, output_path=manifest_path)
    # Now adapter points to empty root but reads via manifest
    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    adapter = GamusAdapter(root=empty_root)
    recs = adapter.list_records(manifest_path=manifest_path)
    assert len(recs) == 1 and recs[0].sample_id == "DC_10_20"
    # get_sample via manifest should still produce sample (paths will be relative to empty_root but exist check deferred)
    sample = adapter.get_sample("DC_10_20", manifest_path=manifest_path, load_arrays=False)
    assert sample is not None and sample.sample_id == "DC_10_20"


def test_adapter_config_env_and_json(tmp_path, monkeypatch):
    # Test GamusConfig integration
    root = tmp_path / "gamus_env"
    _make_root_with_samples(root, ids=["DC_01_25"])
    monkeypatch.setenv("GAMUS_ROOT", str(root))
    cfg = GamusConfig()
    adapter = GamusAdapter(config=cfg)
    assert adapter.root == root.resolve()
    # From JSON
    json_path = tmp_path / "cfg.json"
    import json

    json_path.write_text(json.dumps({"root": str(root), "split": "train"}), encoding="utf-8")
    cfg2 = GamusConfig.from_json(json_path)
    assert cfg2.root == root
    assert cfg2.split == "train"


def test_adapter_lazy_loading_with_h5_mock(tmp_path):
    # Mock _load_array_h5 to avoid needing real H5 files
    import unittest.mock as mock
    import numpy as np

    root = tmp_path / "mock"
    _make_root_with_samples(root, ids=["DC_01_25"])
    adapter = GamusAdapter(root=root)

    fake_image = np.zeros((4, 4, 3), dtype=np.uint8)
    fake_height = np.zeros((4, 4), dtype=np.float32)
    fake_label = np.zeros((4, 4), dtype=np.uint8)

    def fake_load(path):
        name = Path(path).name
        if "RGB" in name:
            return (fake_image, "uint8", "image")
        if "AGL" in name:
            return (fake_height, "float32", "image")
        if "CLS" in name:
            return (fake_label, "uint8", "image")
        raise FileNotFoundError

    with mock.patch("depthwizard.data.adapter._load_array_h5", side_effect=fake_load):
        rec = adapter.list_records()[0]
        sample = adapter.to_sample(rec, load_arrays=True)
        assert sample.image is not None and sample.image.shape == (4, 4, 3)
        assert sample.height is not None and sample.height.shape == (4, 4)
        assert sample.label is not None
        # Ensure dtype semantics preserved
        assert sample.image.dtype == np.uint8
