import tempfile
from pathlib import Path

import pytest

from depthwizard.data.schemas import GamusRecord
from depthwizard.data.validation import validate_records, ValidationReport


def _valid_records():
    return [
        GamusRecord(
            sample_id="DC_03_26",
            image_path="images/train/DC_03_26_RGB.h5",
            height_path="heights/train/DC_03_26_AGL.h5",
            label_path="classes/train/DC_03_26_CLS.h5",
            split="train",
        ),
        GamusRecord(
            sample_id="DC_05_28",
            image_path="images/train/DC_05_28_RGB.h5",
            height_path="heights/train/DC_05_28_AGL.h5",
            label_path="classes/train/DC_05_28_CLS.h5",
            split="train",
        ),
    ]


def test_validation_valid_schema():
    recs = _valid_records()
    report = validate_records(recs, root=None, check_files_exist=False)
    assert report.ok
    assert len(report.errors) == 0


def test_pairing_mismatch_detection():
    # image_path does not match sample_id
    bad = GamusRecord(
        sample_id="DC_03_26",
        image_path="images/train/DC_05_28_RGB.h5",  # wrong id
        height_path="heights/train/DC_03_26_AGL.h5",
        label_path="classes/train/DC_03_26_CLS.h5",
        split="train",
    )
    report = validate_records([bad], root=None, check_files_exist=False)
    assert not report.ok
    assert any(i.code == "pairing_mismatch" and "image_path" in i.field for i in report.errors)


def test_missing_file_detection(tmp_path):
    root = tmp_path / "gamus"
    # Create only image file, not height/label
    (root / "images" / "train").mkdir(parents=True, exist_ok=True)
    (root / "images" / "train" / "DC_03_26_RGB.h5").write_bytes(b"")
    recs = [GamusRecord(
        sample_id="DC_03_26",
        image_path="images/train/DC_03_26_RGB.h5",
        height_path="heights/train/DC_03_26_AGL.h5",
        label_path="classes/train/DC_03_26_CLS.h5",
        split="train",
    )]
    report = validate_records(recs, root=root, check_files_exist=True)
    assert not report.ok
    missing = [i for i in report.errors if i.code == "missing_file"]
    assert len(missing) == 2  # height + label missing
    assert any("height" in i.message for i in missing)


def test_duplicate_detection():
    recs = [
        GamusRecord(sample_id="DC_01_01", image_path="images/train/DC_01_01_RGB.h5", height_path="heights/train/DC_01_01_AGL.h5", label_path="classes/train/DC_01_01_CLS.h5", split="train"),
        GamusRecord(sample_id="DC_01_01", image_path="images/train/DC_01_01_RGB.h5", height_path="heights/train/DC_01_01_AGL.h5", label_path="classes/train/DC_01_01_CLS.h5", split="train"),
    ]
    report = validate_records(recs, root=None, check_files_exist=False)
    assert not report.ok
    assert any(i.code == "duplicate_sample_id" for i in report.errors)


def test_invalid_schema_detection():
    # invalid split
    rec = GamusRecord(sample_id="DC_01_01", image_path="images/train/DC_01_01_RGB.h5", height_path="heights/train/DC_01_01_AGL.h5", label_path="classes/train/DC_01_01_CLS.h5", split="train")
    # mutate via dict
    bad = GamusRecord(
        sample_id="",  # empty
        image_path="images/train/DC_01_01_RGB.h5",
        height_path="heights/train/DC_01_01_AGL.h5",
        label_path="classes/train/DC_01_01_CLS.h5",
        split="train",
    )
    report = validate_records([bad], root=None)
    assert any(i.code == "invalid_sample_id" for i in report.errors)

    # sample_id with path separator
    bad2 = GamusRecord(sample_id="bad/id", image_path="images/train/bad/id_RGB.h5", height_path="heights/train/bad/id_AGL.h5", label_path="classes/train/bad/id_CLS.h5", split="train")
    report2 = validate_records([bad2], root=None)
    assert any(i.code == "invalid_sample_id" for i in report2.errors)

    # invalid class values via probing — we mock _try_probe
    import unittest.mock as mock
    import numpy as np
    # Create temp files for probe_arrays path so files exist
    tmp = Path(tempfile.mkdtemp())
    (tmp / "images" / "train").mkdir(parents=True, exist_ok=True)
    (tmp / "heights" / "train").mkdir(parents=True, exist_ok=True)
    (tmp / "classes" / "train").mkdir(parents=True, exist_ok=True)
    for p in [tmp / "images" / "train" / "DC_01_01_RGB.h5", tmp / "heights" / "train" / "DC_01_01_AGL.h5", tmp / "classes" / "train" / "DC_01_01_CLS.h5"]:
        p.write_bytes(b"dummy")
    rec_good = GamusRecord(sample_id="DC_01_01", image_path="images/train/DC_01_01_RGB.h5", height_path="heights/train/DC_01_01_AGL.h5", label_path="classes/train/DC_01_01_CLS.h5", split="train")
    # Mock probe to return label array with invalid class 99
    fake_label = np.array([[0, 1, 99], [2, 3, 6]], dtype=np.uint8)
    fake_image_shape = (2, 3, 3)
    fake_height_shape = (2, 3)

    def fake_probe(path):
        name = Path(path).name
        if "RGB" in name:
            return (fake_image_shape, "uint8", np.zeros(fake_image_shape, dtype=np.uint8), None)
        if "AGL" in name:
            return (fake_height_shape, "float32", np.zeros(fake_height_shape, dtype=np.float32), None)
        if "CLS" in name:
            return (fake_height_shape, "uint8", fake_label, None)
        return (None, None, None, "not found")

    with mock.patch("depthwizard.data.validation._try_probe", side_effect=fake_probe):
        report3 = validate_records([rec_good], root=tmp, probe_arrays=True)
        assert any(i.code == "invalid_class_value" for i in report3.errors)


def test_shape_mismatch_detection():
    import unittest.mock as mock
    import numpy as np
    import tempfile
    from pathlib import Path

    tmp = Path(tempfile.mkdtemp())
    for sub in ["images/train", "heights/train", "classes/train"]:
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    for fname in ["DC_01_01_RGB.h5", "DC_01_01_AGL.h5", "DC_01_01_CLS.h5"]:
        # Need to map correct dirs
        if "RGB" in fname:
            (tmp / "images" / "train" / fname).write_bytes(b"x")
        elif "AGL" in fname:
            (tmp / "heights" / "train" / fname).write_bytes(b"x")
        else:
            (tmp / "classes" / "train" / fname).write_bytes(b"x")
    rec = GamusRecord(sample_id="DC_01_01", image_path="images/train/DC_01_01_RGB.h5", height_path="heights/train/DC_01_01_AGL.h5", label_path="classes/train/DC_01_01_CLS.h5", split="train")

    # image 1024x1024 vs height 512x512 -> mismatch
    def fake_probe_mismatch(path):
        n = Path(path).name
        if "RGB" in n:
            return ((1024, 1024, 3), "uint8", np.zeros((1024, 1024, 3), dtype=np.uint8), None)
        if "AGL" in n:
            return ((512, 512), "float32", np.zeros((512, 512), dtype=np.float32), None)
        if "CLS" in n:
            return ((1024, 1024), "uint8", np.zeros((1024, 1024), dtype=np.uint8), None)
        return (None, None, None, None)

    with mock.patch("depthwizard.data.validation._try_probe", side_effect=fake_probe_mismatch):
        report = validate_records([rec], root=tmp, probe_arrays=True)
        assert any(i.code == "shape_mismatch" for i in report.errors)


def test_invalid_dtype_warning():
    import unittest.mock as mock
    import numpy as np
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    for sub in ["images/train", "heights/train", "classes/train"]:
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    (tmp / "images" / "train" / "DC_01_01_RGB.h5").write_bytes(b"x")
    (tmp / "heights" / "train" / "DC_01_01_AGL.h5").write_bytes(b"x")
    (tmp / "classes" / "train" / "DC_01_01_CLS.h5").write_bytes(b"x")
    rec = GamusRecord(sample_id="DC_01_01", image_path="images/train/DC_01_01_RGB.h5", height_path="heights/train/DC_01_01_AGL.h5", label_path="classes/train/DC_01_01_CLS.h5", split="train")

    def fake_probe_dtype(path):
        n = Path(path).name
        if "RGB" in n:
            return ((2, 2, 3), "float32", np.zeros((2, 2, 3), dtype=np.float32), None)  # wrong
        if "AGL" in n:
            return ((2, 2), "float32", np.zeros((2, 2)), None)
        if "CLS" in n:
            return ((2, 2), "uint8", np.zeros((2, 2), dtype=np.uint8), None)
        return (None, None, None, None)

    with mock.patch("depthwizard.data.validation._try_probe", side_effect=fake_probe_dtype):
        report = validate_records([rec], root=tmp, probe_arrays=True)
        assert any(i.code == "unexpected_dtype" for i in report.warnings)


def test_validate_without_probe_still_checks_pairing():
    rec = GamusRecord(sample_id="DC_01_01", image_path="images/train/DC_01_01_RGB.h5", height_path="heights/train/DC_01_01_AGL.h5", label_path=None, split="train")
    # label_path None is allowed but height mismatch not checked without probe — but pairing should be ok
    report = validate_records([rec], root=None, probe_arrays=False)
    assert report.ok
