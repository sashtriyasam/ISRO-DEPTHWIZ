import hashlib
from pathlib import Path

import pytest

from depthwizard.data.manifest import discover_records
from depthwizard.data.schemas import GamusRecord
from depthwizard.data.subset import DEFAULT_DEV_SEED, build_dev_manifest, select_development_subset


def _records(ids, split="train"):
    return [
        GamusRecord(
            sample_id=sid,
            image_path=f"images/{split}/{sid}_RGB.h5",
            height_path=f"heights/{split}/{sid}_AGL.h5",
            label_path=f"classes/{split}/{sid}_CLS.h5",
            split=split,
        )
        for sid in ids
    ]


def test_dev_subset_determinism():
    ids = [f"DC_{i:02d}_01" for i in range(10)]
    recs = _records(ids)
    a = select_development_subset(recs, size=5, seed="depthwizard-m1")
    b = select_development_subset(recs, size=5, seed="depthwizard-m1")
    assert [r.sample_id for r in a] == [r.sample_id for r in b]
    # Input order shouldn't matter — shuffle before selecting should give same result
    recs_shuffled = list(reversed(recs))
    c = select_development_subset(recs_shuffled, size=5, seed="depthwizard-m1")
    assert [r.sample_id for r in c] == [r.sample_id for r in a]


def test_dev_subset_seed_sensitivity():
    ids = [f"DC_{i:02d}_01" for i in range(20)]
    recs = _records(ids)
    a = select_development_subset(recs, size=5, seed="seed-A")
    b = select_development_subset(recs, size=5, seed="seed-B")
    # Different seeds should generally give different subsets (cryptographic hash)
    assert [r.sample_id for r in a] != [r.sample_id for r in b]


def test_dev_subset_split_filtering():
    recs = _records(["DC_01_01", "DC_02_01"], split="train") + _records(["DC_03_01", "DC_04_01"], split="val")
    # Selecting from train only should ignore val
    sel = select_development_subset(recs, size=10, seed="s", split_source="train")
    assert all(r.split == "train" for r in sel)
    assert len(sel) == 2
    # Alias handling: 'validation' should map to 'val'
    sel2 = select_development_subset(recs, size=10, seed="s", split_source="validation")
    assert all(r.split == "val" for r in sel2)


def test_dev_subset_size_handling():
    recs = _records([f"DC_{i:02d}" for i in range(5)])
    # size 0 -> empty
    assert select_development_subset(recs, size=0) == []
    # size >= len -> all sorted by hash rank
    all_sorted = select_development_subset(recs, size=100, seed="x")
    assert len(all_sorted) == 5
    # size exact
    five = select_development_subset(recs, size=5, seed="x")
    assert len(five) == 5
    # Hash rank ordering: verify against manual SHA256
    seed = "manual"
    selected = select_development_subset(recs, size=3, seed=seed)
    expected_order = sorted(recs, key=lambda r: (hashlib.sha256(f"{seed}:{r.sample_id}".encode()).hexdigest(), r.sample_id))[:3]
    assert [r.sample_id for r in selected] == [r.sample_id for r in expected_order]


def test_dev_subset_built_manifest_deterministic(tmp_path):
    ids = [f"DC_{i:02d}_01" for i in range(15)]
    recs = _records(ids)
    out = tmp_path / "dev.json"
    m1 = build_dev_manifest(recs, size=6, seed="depthwizard-m1", split_source="train", output_path=out)
    m2 = build_dev_manifest(recs, size=6, seed="depthwizard-m1", split_source="train")
    assert m1["records"] == m2["records"]
    # Check file written is deterministic
    import json

    file_data = json.loads(out.read_text(encoding="utf-8"))
    assert file_data["seed"] == "depthwizard-m1"
    assert file_data["size"] == 6
    assert len(file_data["records"]) == 6
    # Two builds to different files should be byte-identical
    out2 = tmp_path / "dev2.json"
    build_dev_manifest(recs, size=6, seed="depthwizard-m1", split_source="train", output_path=out2)
    assert out.read_bytes() == out2.read_bytes()


def test_dev_subset_not_representative_claim():
    # Just ensure we don't claim representativeness — we test that subset is small subset, not benchmark
    recs = _records([f"DC_{i:02d}" for i in range(100)])
    dev = select_development_subset(recs, size=20, seed=DEFAULT_DEV_SEED)
    assert len(dev) == 20
    # Ensure default seed matches expectation
    assert DEFAULT_DEV_SEED == "depthwizard-m1"
