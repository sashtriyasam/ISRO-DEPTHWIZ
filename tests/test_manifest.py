import json
import os
from pathlib import Path

import pytest

from depthwizard.data.manifest import build_manifest, discover_records, load_manifest
from depthwizard.data.schemas import GamusRecord


def _make_fake_root(tmp_path: Path, split_samples: dict):
    """Create fake GAMUS root with empty .h5 files for given split->list[sample_id]."""
    for split, ids in split_samples.items():
        (tmp_path / "images" / split).mkdir(parents=True, exist_ok=True)
        (tmp_path / "heights" / split).mkdir(parents=True, exist_ok=True)
        (tmp_path / "classes" / split).mkdir(parents=True, exist_ok=True)
        for sid in ids:
            (tmp_path / "images" / split / f"{sid}_RGB.h5").write_bytes(b"")  # empty placeholder
            (tmp_path / "heights" / split / f"{sid}_AGL.h5").write_bytes(b"")
            (tmp_path / "classes" / split / f"{sid}_CLS.h5").write_bytes(b"")


def test_manifest_determinism(tmp_path):
    """Same input -> same manifest (byte-identical ordering) irrespective of filesystem order."""
    root = tmp_path / "gamus"
    # Create files in reverse order on purpose
    ids = ["DC_03_26", "DC_05_28", "DC_01_25"]
    _make_fake_root(root, {"train": list(reversed(ids)), "val": ["DC_99_01"]})
    m1 = build_manifest(root, probe=False, checksum=False)
    m2 = build_manifest(root, probe=False, checksum=False)
    assert m1 == m2
    # Check byte-identical JSON
    out1 = tmp_path / "m1.json"
    out2 = tmp_path / "m2.json"
    build_manifest(root, output_path=out1, probe=False)
    build_manifest(root, output_path=out2, probe=False)
    assert out1.read_bytes() == out2.read_bytes()


def test_manifest_stable_ordering(tmp_path):
    """Ordering must be deterministic: sorted by (split_order, sample_id)."""
    root = tmp_path / "gamus2"
    _make_fake_root(root, {"test": ["DC_10_20", "DC_03_26"], "train": ["DC_05_28", "DC_01_25"]})
    recs = discover_records(root, probe=False)
    # Expected order: train first (GAMUS_SPLITS order train,val,test), then test, each sorted lexicographically
    expected = ["DC_01_25", "DC_05_28", "DC_03_26", "DC_10_20"]
    assert [r.sample_id for r in recs] == expected
    assert [r.split for r in recs] == ["train", "train", "test", "test"]
    # Also check splits param reordering doesn't affect final order
    recs2 = discover_records(root, splits=["test", "train"], probe=False)
    assert [r.sample_id for r in recs2] == expected


def test_manifest_filesystem_order_independence(tmp_path):
    """Do not depend on os.listdir order — monkeypatch to return shuffled."""
    root = tmp_path / "gamus3"
    _make_fake_root(root, {"train": ["DC_01_25", "DC_02_30", "DC_03_26"]})
    original_listdir = os.listdir

    def shuffled_listdir(p):
        files = original_listdir(p)
        return list(reversed(files))  # reverse order

    import unittest.mock as mock

    with mock.patch("os.listdir", side_effect=shuffled_listdir):
        recs_shuffled = discover_records(root, probe=False)
    recs_normal = discover_records(root, probe=False)
    assert [r.sample_id for r in recs_shuffled] == [r.sample_id for r in recs_normal]


def test_manifest_only_supported_fields(tmp_path):
    root = tmp_path / "gamus4"
    _make_fake_root(root, {"train": ["DC_01_25"]})
    recs = discover_records(root, probe=False)
    assert len(recs) == 1
    r = recs[0]
    # Should contain sample_id, image_path etc but not invented fields like absolute elevation
    d = r.to_dict()
    assert "sample_id" in d and d["sample_id"] == "DC_01_25"
    assert d["image_path"] == "images/train/DC_01_25_RGB.h5"
    assert d["height_path"] == "heights/train/DC_01_25_AGL.h5"
    assert d["label_path"] == "classes/train/DC_01_25_CLS.h5"
    assert d["source"] == "gamus"
    # Optional enrichment may be None but must exist as keys
    assert "checksum" in d
    assert "width" in d

    # Verify manifest JSON sorting of keys
    manifest = build_manifest(root)
    j = json.dumps(manifest, sort_keys=True)
    # load_manifest should re-sort records deterministically even if input unsorted
    unsorted_path = tmp_path / "unsorted.json"
    # Write manually unsorted records to test load_manifest re-sorting
    unsorted_manifest = dict(manifest)
    unsorted_manifest["records"] = list(reversed(manifest["records"])) if len(manifest["records"]) > 1 else manifest["records"]
    unsorted_path.write_text(json.dumps(unsorted_manifest), encoding="utf-8")
    loaded = load_manifest(unsorted_path)
    assert [r["sample_id"] for r in loaded["records"]] == sorted([r["sample_id"] for r in loaded["records"]])


def test_discover_records_legacy_suffix(tmp_path):
    """Should accept legacy _IMG.h5 images via _strip_image_suffix."""
    root = tmp_path / "legacy"
    (root / "images" / "train").mkdir(parents=True, exist_ok=True)
    (root / "heights" / "train").mkdir(parents=True, exist_ok=True)
    (root / "classes" / "train").mkdir(parents=True, exist_ok=True)
    (root / "images" / "train" / "DC_01_25_IMG.h5").write_bytes(b"")
    (root / "heights" / "train" / "DC_01_25_AGL.h5").write_bytes(b"")
    (root / "classes" / "train" / "DC_01_25_CLS.h5").write_bytes(b"")
    recs = discover_records(root)
    assert len(recs) == 1
    assert recs[0].sample_id == "DC_01_25"


def test_manifest_checksum_and_probe_optional(tmp_path):
    root = tmp_path / "probe"
    _make_fake_root(root, {"train": ["DC_01_25"]})
    # checksum on empty file should produce sha256 of empty bytes
    recs = discover_records(root, checksum=True)
    # empty file has known sha256
    import hashlib

    empty_hash = hashlib.sha256(b"").hexdigest()
    assert recs[0].checksum == empty_hash
    # probe without h5py falls back to None dimensions—should not fail
    recs2 = discover_records(root, probe=True)
    assert recs2[0].sample_id == "DC_01_25"
