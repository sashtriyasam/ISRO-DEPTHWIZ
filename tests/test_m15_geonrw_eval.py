"""Tests for M15 GeoNRW external eval helpers (mocked; no GPU, no weights, no downloads)."""

import pytest

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")
rasterio = pytest.importorskip("rasterio")


def test_m15_parse_triplet_stem():
    from depthwizard.experiments.m15_geonrw_eval import parse_triplet_stem

    assert parse_triplet_stem("368_5702_rgb.jp2") == ("368_5702", "rgb")
    assert parse_triplet_stem("368_5702_dem.tif") == ("368_5702", "dem")
    assert parse_triplet_stem("368_5702_seg.tif") == ("368_5702", "seg")
    assert parse_triplet_stem("random.txt") is None
    assert parse_triplet_stem("368_5702_rgb.tif") is None  # wrong ext never misgrouped


def test_m15_enumerate_sorted_and_complete_only(tmp_path):
    from depthwizard.experiments.m15_geonrw_eval import enumerate_triplets

    (tmp_path / "b_city").mkdir()
    (tmp_path / "a_city").mkdir()
    for name in ["2_2_rgb.jp2", "2_2_dem.tif", "1_1_rgb.jp2", "1_1_dem.tif", "9_9_rgb.jp2"]:
        (tmp_path / "a_city" / name).write_bytes(b"x")
    (tmp_path / "b_city" / "0_0_rgb.jp2").write_bytes(b"x")
    (tmp_path / "b_city" / "0_0_dem.tif").write_bytes(b"x")
    items = enumerate_triplets(tmp_path)
    # incomplete (9_9, rgb-only) excluded; sorted by (city, stem)
    assert [(i["city"], i["stem"]) for i in items] == [
        ("a_city", "1_1"), ("a_city", "2_2"), ("b_city", "0_0"),
    ]


def _mem_gtiff(path, arr, transform, crs="EPSG:25832", nodata=None, count=1):
    import rasterio

    profile = {"driver": "GTiff", "height": arr.shape[0], "width": arr.shape[1],
               "count": count, "dtype": arr.dtype.name, "crs": crs, "transform": transform,
               "nodata": nodata}
    with rasterio.open(path, "w", **profile) as ds:
        if count == 1:
            ds.write(arr, 1)
        else:
            for i in range(count):
                ds.write(arr[:, :, i], i + 1)


def test_m15_load_triplet_grids_must_match(tmp_path):
    from rasterio.transform import from_origin

    from depthwizard.experiments.m15_geonrw_eval import load_triplet

    rgb = (np.zeros((10, 10, 4), dtype=np.uint8))
    dem = np.ones((10, 10), dtype=np.float32)
    rp, dp = str(tmp_path / "a_rgb.jp2"), str(tmp_path / "a_dem.tif")
    _mem_gtiff(rp, rgb, from_origin(0, 10, 1, 1), count=4)
    _mem_gtiff(dp, dem, from_origin(0, 10, 1, 1))
    sample = load_triplet(rp, dp)
    assert sample["image"].shape == (10, 10, 3)
    assert sample["image"].dtype == np.uint8
    # mismatched transform must raise, never resample silently
    dp2 = str(tmp_path / "b_dem.tif")
    _mem_gtiff(dp2, dem, from_origin(5, 10, 1, 1))
    with pytest.raises(ValueError):
        load_triplet(rp, dp2)


def test_m15_shared_horizontal_frame():
    from depthwizard.experiments.m15_geonrw_eval import shares_horizontal_frame

    assert shares_horizontal_frame("EPSG:25832", "EPSG:25832") is True
    dem_wkt = ('LOCAL_CS["ETRS89 / UTM zone 32N + DHHN92 height",'
               'UNIT["metre",1,AUTHORITY["EPSG","9001"]]]')
    assert shares_horizontal_frame("EPSG:25832", dem_wkt) is True
    assert shares_horizontal_frame("EPSG:25832", "EPSG:32633") is False


def test_m15_nodata_to_nan_and_negatives_kept(tmp_path):
    from rasterio.transform import from_origin

    from depthwizard.experiments.m15_geonrw_eval import load_triplet

    rgb = np.zeros((4, 4, 4), dtype=np.uint8)
    dem = np.full((4, 4), 100.0, dtype=np.float32)
    dem[0, 0] = -9999.0
    dem[1, 1] = -2.5
    rp, dp = str(tmp_path / "a_rgb.jp2"), str(tmp_path / "a_dem.tif")
    _mem_gtiff(rp, rgb, from_origin(0, 4, 1, 1), count=4)
    _mem_gtiff(dp, dem, from_origin(0, 4, 1, 1), nodata=-9999.0)
    sample = load_triplet(rp, dp)
    assert bool(np.isnan(sample["height"][0, 0]))
    assert sample["height"][1, 1] == pytest.approx(-2.5)
    assert sample["geo"]["dem_nodata_tag"] == -9999.0


def test_m15_evaluate_triplet_affine_and_diagnostic():
    from depthwizard.experiments.m15_geonrw_eval import evaluate_triplet

    rng = np.random.default_rng(0)
    target = rng.normal(100.0, 10.0, size=(32, 32))
    pred = (target - 90.0) / 5.0  # exact affine relation: target = 5*pred + 90
    ev = evaluate_triplet(pred, target)
    assert ev["aligned_mae"] == pytest.approx(0.0, abs=1e-6)
    assert ev["affine_a"] == pytest.approx(5.0)
    assert ev["affine_b"] == pytest.approx(90.0)
    assert ev["pearson"] == pytest.approx(1.0)
    assert ev["direct_mae_diagnostic"] > 1.0  # datum-offset dominated by construction
    assert ev["n_valid"] == 32 * 32
    assert ev["degenerate"] is False


def test_m15_evaluate_triplet_zero_valid_raises():
    from depthwizard.experiments.m15_geonrw_eval import evaluate_triplet

    with pytest.raises(ValueError):
        evaluate_triplet(
            np.full((4, 4), np.nan), np.full((4, 4), np.nan),
        )


def test_m15_frozen_m10_constants():
    import pathlib

    src = pathlib.Path("src/depthwizard/experiments/m15_geonrw_eval.py").read_text(encoding="utf-8")
    assert "8.037330237035235" in src and "10.304011604437477" in src
    assert "M10_BEST_EPOCH = 22" in src
