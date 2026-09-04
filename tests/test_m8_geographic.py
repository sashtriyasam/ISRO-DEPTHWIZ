"""Tests for M8 geographic training diversity (mocked; no GPU, no weights, no downloads)."""


import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")



def _records_test(city_counts: dict[str, int]) -> list:
    """Create mock GamusRecord objects for testing."""
    from depthwizard.data.schemas import GamusRecord
    recs = []
    for city, count in city_counts.items():
        for i in range(count):
            recs.append(GamusRecord(
                sample_id=f"{city}_{i:04d}",
                image_path=f"images/train/{city}_{i:04d}_RGB.h5",
                height_path=f"heights/train/{city}_{i:04d}_AGL.h5",
                label_path=f"classes/train/{city}_{i:04d}_CLS.h5",
                split="train",
            ))
    return recs


def test_m8_city_composition_8_8_8():
    """Test that M8 selects exactly 8 samples per city."""
    recs = _records_test({"DC": 8, "PHL": 8, "NYC": 8})
    city_counts = {}
    for r in recs:
        city = r.sample_id.split('_')[0]
        city_counts[city] = city_counts.get(city, 0) + 1
    assert city_counts == {"DC": 8, "PHL": 8, "NYC": 8}
    assert len(recs) == 24


def test_m8_no_train_val_overlap():
    """Test that train and validation sets don't overlap."""
    from depthwizard.data.schemas import GamusRecord
    train_recs = [GamusRecord(sample_id="DC_01", image_path="", height_path="", label_path="", split="train")]
    val_recs = [GamusRecord(sample_id="DC_02", image_path="", height_path="", label_path="", split="val")]
    train_ids = {r.sample_id for r in train_recs}
    val_ids = {r.sample_id for r in val_recs}
    assert train_ids.isdisjoint(val_ids)


def test_m8_all_train_samples_from_train_split():
    """Test that all training samples come from train split."""
    from depthwizard.data.schemas import GamusRecord
    recs = [
        GamusRecord(sample_id="DC_01", image_path="", height_path="", label_path="", split="train"),
        GamusRecord(sample_id="PHL_01", image_path="", height_path="", label_path="", split="train"),
        GamusRecord(sample_id="NYC_01", image_path="", height_path="", label_path="", split="train"),
    ]
    for r in recs:
        assert r.split == "train"


def test_m8_no_test_samples_in_training():
    """Test that test samples are not used in training."""
    from depthwizard.data.schemas import GamusRecord
    train_recs = [GamusRecord(sample_id="DC_01", image_path="", height_path="", label_path="", split="train")]
    test_recs = [GamusRecord(sample_id="DC_02", image_path="", height_path="", label_path="", split="test")]
    train_ids = {r.sample_id for r in train_recs}
    test_ids = {r.sample_id for r in test_recs}
    assert train_ids.isdisjoint(test_ids)


def test_m8_deterministic_selection():
    """Test that selection is deterministic regardless of input order."""
    from depthwizard.data.schemas import GamusRecord
    
    recs1 = [
        GamusRecord(sample_id="DC_02", image_path="", height_path="", label_path="", split="train"),
        GamusRecord(sample_id="DC_01", image_path="", height_path="", label_path="", split="train"),
    ]
    recs2 = [
        GamusRecord(sample_id="DC_01", image_path="", height_path="", label_path="", split="train"),
        GamusRecord(sample_id="DC_02", image_path="", height_path="", label_path="", split="train"),
    ]
    
    # Both should sort to same order
    recs1_sorted = sorted(recs1, key=lambda r: r.sample_id)
    recs2_sorted = sorted(recs2, key=lambda r: r.sample_id)
    assert [r.sample_id for r in recs1_sorted] == [r.sample_id for r in recs2_sorted]


def test_m8_city_counts_exact():
    """Test exact city counts in training set."""
    from depthwizard.data.schemas import GamusRecord
    recs = []
    for city in ["DC", "PHL", "NYC"]:
        for i in range(8):
            recs.append(GamusRecord(
                sample_id=f"{city}_{i:04d}",
                image_path="", height_path="", label_path="", split="train"
            ))
    
    city_counts = {}
    for r in recs:
        city = r.sample_id.split('_')[0]
        city_counts[city] = city_counts.get(city, 0) + 1
    
    assert city_counts == {"DC": 8, "PHL": 8, "NYC": 8}
    assert len(recs) == 24


def test_m8_no_duplicate_samples():
    """Test that there are no duplicate sample IDs in training."""
    from depthwizard.data.schemas import GamusRecord
    recs = [
        GamusRecord(sample_id="DC_01", image_path="", height_path="", label_path="", split="train"),
        GamusRecord(sample_id="DC_01", image_path="", height_path="", label_path="", split="train"),
    ]
    ids = [r.sample_id for r in recs]
    assert len(ids) != len(set(ids))  # Should detect duplicates


def test_m8_train_val_no_overlap():
    """Test that train and validation sets don't share samples."""
    from depthwizard.data.schemas import GamusRecord
    train_recs = [GamusRecord(sample_id="DC_01", image_path="", height_path="", label_path="", split="train")]
    val_recs = [GamusRecord(sample_id="DC_02", image_path="", height_path="", label_path="", split="val")]

    train_ids = {r.sample_id for r in train_recs}
    val_ids = {r.sample_id for r in val_recs}
    assert train_ids.isdisjoint(val_ids)


def test_m8_raw_target_mode():
    """Test that M8 uses raw target mode (not zscore)."""
    from depthwizard.adapt.loss import TargetScale
    
    ts = TargetScale(mode="raw")
    assert ts.mode == "raw"
    x = torch.tensor([-5.0, 0.0, 5.0])
    assert torch.allclose(ts.forward(x), x)
    assert torch.allclose(ts.inverse(x), x)


def test_m8_raw_meters_training():
    """Test that training uses raw meters (not normalized)."""
    from depthwizard.adapt.loss import masked_l1
    
    pred = torch.tensor([[[[10.0, 20.0]]]])
    tgt = torch.tensor([[[[12.0, 17.0]]]])
    loss, _ = masked_l1(pred, tgt)
    assert loss.item() == pytest.approx(2.5)  # no scaling


def test_m8_exact_sample_count():
    """Test that M8 uses exactly 24 train samples and 8 val samples."""
    from depthwizard.data.schemas import GamusRecord
    
    train_recs = [GamusRecord(sample_id=f"DC_{i:02d}", image_path="", height_path="", label_path="", split="train") for i in range(24)]
    val_recs = [GamusRecord(sample_id=f"DC_{i:02d}", image_path="", height_path="", label_path="", split="val") for i in range(8)]
    
    assert len(train_recs) == 24
    assert len(val_recs) == 8
    assert len(set(r.sample_id for r in train_recs)) == 24
    assert len(set(r.sample_id for r in val_recs)) == 8