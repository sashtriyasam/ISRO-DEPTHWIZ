"""Tests for the experiment-ready data interface (synthetic fixtures; torch optional)."""

from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
h5py = pytest.importorskip("h5py")

from depthwizard.data.experiment import (  # noqa: E402
    GamusExperimentDataset,
    height_to_tensor,
    image_to_tensor,
    label_to_tensor,
)
from depthwizard.data.manifest import build_manifest  # noqa: E402
from depthwizard.data.schemas import GamusRecord  # noqa: E402


def _write_h5(path: Path, arr, key: str = "image") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(str(path), "w") as f:
        f.create_dataset(key, data=arr)
    return path


def _root(tmp: Path, sid: str = "DC_01_25", h: int = 8, w: int = 8, seed: int = 0):
    rng = np.random.default_rng(seed)
    _write_h5(tmp / f"images/train/{sid}_RGB.h5", rng.integers(0, 256, (h, w, 3)).astype(np.uint8))
    _write_h5(tmp / f"heights/train/{sid}_AGL.h5", rng.uniform(0, 30, (h, w)).astype(np.float32))
    _write_h5(tmp / f"classes/train/{sid}_CLS.h5", rng.integers(0, 7, (h, w)).astype(np.float32))
    return tmp


def _rec(sid: str, split: str = "train") -> GamusRecord:
    return GamusRecord(
        sample_id=sid,
        image_path=f"images/{split}/{sid}_RGB.h5",
        height_path=f"heights/{split}/{sid}_AGL.h5",
        label_path=f"classes/{split}/{sid}_CLS.h5",
        split=split,
    )


def test_image_tensor_shape_dtype_range():
    img = (np.arange(48).reshape(4, 4, 3) % 256).astype(np.uint8)
    t = image_to_tensor(img)
    assert tuple(t.shape) == (3, 4, 4)
    assert str(t.dtype) in ("torch.float32", "float32")
    assert float(t.min()) >= 0.0 and float(t.max()) <= 1.0


def test_image_tensor_rejects_wrong_dtype_or_rank():
    with pytest.raises(ValueError):
        image_to_tensor(np.zeros((4, 4, 3), dtype=np.float32))  # must be raw uint8
    with pytest.raises(ValueError):
        image_to_tensor(np.zeros((4, 4), dtype=np.uint8))  # must be HWC


def test_height_tensor_shape_dtype_unclipped():
    h = height_to_tensor(np.array([[-5.0, 0.0], [44.5, 100.0]], dtype=np.float32))
    assert tuple(h.shape) == (1, 2, 2)
    assert float(h.max()) == 100.0  # never clipped
    assert float(h.min()) == -5.0  # negatives preserved for analysis


def test_label_tensor_float_storage_rounding_and_validation():
    t = label_to_tensor(np.array([[0.0, 1.0], [6.0, 3.0]], dtype=np.float32))
    assert tuple(t.shape) == (2, 2) and "int64" in str(t.dtype)
    with pytest.raises(ValueError):
        label_to_tensor(np.array([[0.0, 1.5]], dtype=np.float32))  # non-integer
    with pytest.raises(ValueError):
        label_to_tensor(np.array([[0, 99]], dtype=np.uint8))  # out of contract


def test_dataset_manifest_driven_lookup_and_determinism(tmp_path):
    _root(tmp_path, sid="DC_02_24", seed=1)
    _root(tmp_path, sid="DC_01_25", seed=2)
    recs = [_rec("DC_02_24"), _rec("DC_01_25")]  # shuffled input order
    ds = GamusExperimentDataset(records=recs, root=tmp_path)
    assert ds.sample_ids() == ["DC_01_25", "DC_02_24"]  # sorted internally
    a = ds[0]
    assert a["sample_id"] == "DC_01_25"
    assert tuple(a["image"].shape) == (3, 8, 8)
    assert tuple(a["height"].shape) == (1, 8, 8)
    assert tuple(a["label"].shape) == (8, 8)
    # Deterministic: same index twice -> same sample.
    assert ds[0]["sample_id"] == ds[0]["sample_id"]


def test_dataset_from_manifest_file(tmp_path):
    _root(tmp_path, sid="DC_01_25")
    mp = tmp_path / "m.json"
    build_manifest(tmp_path, output_path=mp)
    ds = GamusExperimentDataset(manifest_path=mp, root=tmp_path)
    assert len(ds) == 1 and ds[0]["sample_id"] == "DC_01_25"
    assert ds.manifest_revision()["count"] == 1


def test_dataset_requires_explicit_records_or_manifest(tmp_path):
    with pytest.raises(ValueError):
        GamusExperimentDataset(root=tmp_path)
    with pytest.raises(ValueError):
        GamusExperimentDataset(records=[_rec("DC_01_25")], manifest_path=tmp_path / "m.json")


def test_dataset_missing_h5_raises_not_silent(tmp_path):
    ds = GamusExperimentDataset(records=[_rec("DC_99_99")], root=tmp_path)
    with pytest.raises(FileNotFoundError):
        ds[0]


def test_dataset_malformed_h5_raises(tmp_path):
    _root(tmp_path, sid="DC_01_25")
    (tmp_path / "heights/train/DC_01_25_AGL.h5").write_bytes(b"corrupt")
    ds = GamusExperimentDataset(records=[_rec("DC_01_25")], root=tmp_path)
    with pytest.raises(Exception):
        ds[0]


def test_dataset_shape_mismatch_raises(tmp_path):
    _root(tmp_path, sid="DC_01_25", h=8, w=8)
    _write_h5(tmp_path / "heights/train/DC_01_25_AGL.h5", np.zeros((4, 8), np.float32))
    ds = GamusExperimentDataset(records=[_rec("DC_01_25")], root=tmp_path)
    with pytest.raises(ValueError, match="[Ss]hape mismatch"):
    # cross-modal class mismatch likewise
        ds[0]


def test_dataset_class_mismatch_raises(tmp_path):
    _root(tmp_path, sid="DC_01_25", h=8, w=8)
    _write_h5(tmp_path / "classes/train/DC_01_25_CLS.h5", np.zeros((4, 8), np.float32))
    ds = GamusExperimentDataset(records=[_rec("DC_01_25")], root=tmp_path)
    with pytest.raises(ValueError, match="[Ss]hape mismatch"):
        ds[0]


def test_dataset_invalid_class_raises(tmp_path):
    _root(tmp_path, sid="DC_01_25")
    _write_h5(tmp_path / "classes/train/DC_01_25_CLS.h5", np.full((8, 8), 99, np.float32))
    ds = GamusExperimentDataset(records=[_rec("DC_01_25")], root=tmp_path)
    with pytest.raises(ValueError, match="[Cc]lass"):
        ds[0]


def test_dataset_nan_height_propagates_with_metadata(tmp_path):
    _root(tmp_path, sid="DC_01_25")
    arr = np.zeros((8, 8), np.float32)
    arr[0, 0] = float("nan")
    _write_h5(tmp_path / "heights/train/DC_01_25_AGL.h5", arr)
    ds = GamusExperimentDataset(records=[_rec("DC_01_25")], root=tmp_path)
    item = ds[0]  # raw values preserved (probe layer reports NaN; dataset does not clip)
    assert item["height"] is not None
    assert item["metadata"]["height_is_ndsm_agl_ground_truth"] is True


def test_dataset_metadata_propagation(tmp_path):
    _root(tmp_path, sid="DC_01_25")
    ds = GamusExperimentDataset(records=[_rec("DC_01_25")], root=tmp_path)
    item = ds[0]
    assert item["metadata"]["source"] == "gamus"
    assert "CHW" in item["metadata"]["tensor_spec"]
    assert item["split"] == "train"


def test_dataset_split_filtering_preserves_gamus_splits(tmp_path):
    _root(tmp_path, sid="DC_01_25")
    (tmp_path / "images/val").mkdir(parents=True, exist_ok=True)
    (tmp_path / "heights/val").mkdir(parents=True, exist_ok=True)
    (tmp_path / "classes/val").mkdir(parents=True, exist_ok=True)
    import shutil

    for mod, suf in (("images", "RGB"), ("heights", "AGL"), ("classes", "CLS")):
        shutil.copy(tmp_path / f"{mod}/train/DC_01_25_{suf}.h5", tmp_path / f"{mod}/val/DC_01_25_{suf}.h5")
    recs = [_rec("DC_01_25", "train"), _rec("DC_01_25", "val")]
    ds = GamusExperimentDataset(records=recs, root=tmp_path, split="val")
    assert len(ds) == 1 and ds[0]["split"] == "val"
