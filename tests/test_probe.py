"""Tests for the empirical H5 probe (synthetic fixtures; no network, no real data)."""

import json
from pathlib import Path

import pytest

h5py = pytest.importorskip("h5py")
np = pytest.importorskip("numpy")

from depthwizard.data.manifest import build_manifest  # noqa: E402
from depthwizard.data.probe import (  # noqa: E402
    probe_modality,
    probe_records,
    probe_record,
    probe_root,
    render_markdown,
    write_report,
)
from depthwizard.data.schemas import GamusRecord  # noqa: E402


def _write_h5(path: Path, arr, key: str = "image") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(str(path), "w") as f:
        f.create_dataset(key, data=arr)
    return path


def _rec(sid: str = "DC_01_25", split: str = "train") -> GamusRecord:
    return GamusRecord(
        sample_id=sid,
        image_path=f"images/{split}/{sid}_RGB.h5",
        height_path=f"heights/{split}/{sid}_AGL.h5",
        label_path=f"classes/{split}/{sid}_CLS.h5",
        split=split,
    )


def _root_with_sample(tmp: Path, sid: str = "DC_01_25", h: int = 8, w: int = 8):
    rng = np.random.default_rng(0)
    _write_h5(tmp / f"images/train/{sid}_RGB.h5", rng.integers(0, 256, (h, w, 3)).astype(np.uint8))
    _write_h5(tmp / f"heights/train/{sid}_AGL.h5", rng.uniform(0, 30, (h, w)).astype(np.float32))
    _write_h5(tmp / f"classes/train/{sid}_CLS.h5", rng.integers(0, 7, (h, w)).astype(np.float32))
    return tmp


def test_probe_rgb_shape_dtype_range(tmp_path):
    p = _write_h5(tmp_path / "img.h5", np.arange(48, dtype=np.uint8).reshape(4, 4, 3))
    d = probe_modality(p, "image")
    assert d["shape"] == [4, 4, 3] and d["dtype"] == "uint8" and d["h5_key"] == "image"
    assert d["min"] == 0.0 and d["max"] == 47.0 and d["finite_pct"] == 100.0
    assert d["in_uint8_range"] is True


def test_probe_legacy_data_key(tmp_path):
    p = _write_h5(tmp_path / "img.h5", np.zeros((4, 4, 3), np.uint8), key="data")
    assert probe_modality(p, "image")["h5_key"] == "data"


def test_probe_unsupported_key_raises(tmp_path):
    p = tmp_path / "empty.h5"
    with h5py.File(str(p), "w") as f:
        f.attrs["note"] = "no datasets here"
    with pytest.raises(KeyError):
        probe_modality(p, "image")


def test_probe_malformed_h5_raises(tmp_path):
    p = tmp_path / "bad.h5"
    p.write_bytes(b"not an hdf5 file at all")
    with pytest.raises(Exception):
        probe_modality(p, "image")


def test_probe_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        probe_modality(tmp_path / "nope.h5", "height")


def test_probe_height_nan_inf_negative(tmp_path):
    arr = np.array([[0.0, 1.0, float("nan")], [float("inf"), -2.5, 3.0]], dtype=np.float32)
    d = probe_modality(_write_h5(tmp_path / "h.h5", arr), "height")
    assert d["nan"] == 1 and d["inf"] == 1
    assert abs(d["finite_pct"] - 100.0 * 4 / 6) < 1e-9
    assert d["negative"] == 1 and d["zero"] == 1
    assert d["min"] == -2.5 and d["max"] == 3.0
    assert set(d["percentiles"]) == {"p0", "p1", "p5", "p25", "p50", "p75", "p95", "p99", "p100"}


def test_probe_height_sentinel_candidate(tmp_path):
    arr = np.zeros((10, 10), dtype=np.float32)
    arr[:2, :] = -5.0  # 20 of 100 pixels = 20% >= 1% threshold
    d = probe_modality(_write_h5(tmp_path / "h.h5", arr), "height")
    cands = {c["value"]: c["count"] for c in d["sentinel_candidates"]}
    assert cands.get(-5.0) == 20


def test_probe_label_float_storage_uniques(tmp_path):
    arr = np.array([[0, 1, 6], [3, 3, 5]], dtype=np.float32)
    d = probe_modality(_write_h5(tmp_path / "c.h5", arr), "label")
    assert d["classes"]["integer_valued"] is True
    assert d["classes"]["invalid_values"] == []
    assert d["classes"]["n_unique"] == 5


def test_probe_label_invalid_values(tmp_path):
    arr = np.array([[0, 7], [99, 3]], dtype=np.float32)
    d = probe_modality(_write_h5(tmp_path / "c.h5", arr), "label")
    assert d["classes"]["invalid_values"] == [7.0, 99.0]


def test_probe_record_alignment_ok(tmp_path):
    _root_with_sample(tmp_path)
    r = probe_record(_rec(), tmp_path)
    assert r["aligned"] is True and r["errors"] == []
    assert r["spatial_shapes"] == {"image": [8, 8], "height": [8, 8], "label": [8, 8]}


def test_probe_record_mismatch_reported_not_resized(tmp_path):
    _root_with_sample(tmp_path, h=8, w=8)
    # Overwrite height with a different spatial extent.
    _write_h5(tmp_path / "heights/train/DC_01_25_AGL.h5", np.zeros((4, 8), np.float32))
    r = probe_record(_rec(), tmp_path)
    assert r["aligned"] is False
    assert any("mismatch" in e for e in r["errors"])


def test_probe_records_deterministic_order_and_report(tmp_path):
    _root_with_sample(tmp_path, sid="DC_02_24")
    _root_with_sample(tmp_path, sid="DC_01_25")
    recs = [
        _rec("DC_02_24"),
        _rec("DC_01_25"),
    ]
    rep = probe_records(recs, tmp_path)
    assert rep["sample_ids"] == ["DC_01_25", "DC_02_24"]
    assert rep["n_samples"] == 2
    assert rep["mismatched_shape_count"] == 0
    assert "probe_timestamp_utc" in rep  # metadata only


def test_probe_root_and_manifest_probe_integration(tmp_path):
    _root_with_sample(tmp_path, sid="DC_01_25")
    manifest_path = tmp_path / "m.json"
    build_manifest(tmp_path, output_path=manifest_path, probe=True, checksum=False)
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert m["records"][0]["image_dtype"] == "uint8"
    assert m["records"][0]["width"] == 8
    rep = probe_root(tmp_path)
    assert rep["n_samples"] == 1 and rep["samples"][0]["aligned"] is True


def test_write_report_and_markdown_roundtrip(tmp_path):
    _root_with_sample(tmp_path)
    rep = probe_root(tmp_path)
    out = write_report(rep, tmp_path / "probe.json")
    assert json.loads(out.read_text(encoding="utf-8"))["n_samples"] == 1
    md = render_markdown(rep)
    assert "DC_01_25" in md and "uint8" in md and "aligned=True" in md
