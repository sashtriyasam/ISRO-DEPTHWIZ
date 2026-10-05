"""validate_dsm: metric comparison when georeferenced, correlation-only otherwise."""

from pathlib import Path

import numpy as np
import pytest

from depthwizard.errors import InvalidInputError
from depthwizard.evaluation.validate import validate_dsm


def _raster(path: Path, data: np.ndarray, crs: str | None, pixel: float = 1.0) -> Path:
    import rasterio
    from rasterio.transform import from_origin

    profile = {
        "driver": "GTiff",
        "width": data.shape[1],
        "height": data.shape[0],
        "count": 1,
        "dtype": "float32",
        "nodata": float("nan"),
    }
    if crs:
        profile.update(crs=crs, transform=from_origin(500000, 3000000, pixel, pixel))
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data.astype("float32"), 1)
    return path


def test_metric_scores_against_georeferenced_reference(tmp_path: Path) -> None:
    rows, cols = np.mgrid[0:60, 0:60]
    truth = 100.0 + rows * 0.5
    product = _raster(tmp_path / "dsm.tif", truth + 2.0, "EPSG:32643")
    reference = _raster(tmp_path / "ref.tif", truth, "EPSG:32643")
    report = validate_dsm(product, reference)
    assert report["metric"] is True
    native = report["native"]
    assert native["bias"] == pytest.approx(2.0, abs=1e-4)
    assert native["rmse"] == pytest.approx(2.0, abs=1e-4)
    assert native["pearson_r"] == pytest.approx(1.0)
    assert report["coarse"]["rmse"] == pytest.approx(2.0, abs=1e-3)


def test_relative_product_reports_correlation_only(tmp_path: Path) -> None:
    rows, _ = np.mgrid[0:40, 0:40]
    product = _raster(tmp_path / "rdsm.tif", rows * 0.01, None)
    reference = _raster(tmp_path / "ref.tif", 50.0 + rows * 3.0, "EPSG:32643")
    report = validate_dsm(product, reference)
    assert report["metric"] is False
    assert report["native"]["rmse"] is None
    assert report["native"]["spearman_rho"] == pytest.approx(1.0, abs=1e-6)
    assert "note" in report


def test_missing_files_are_refused(tmp_path: Path) -> None:
    with pytest.raises(InvalidInputError, match="not found"):
        validate_dsm(tmp_path / "a.tif", tmp_path / "b.tif")
