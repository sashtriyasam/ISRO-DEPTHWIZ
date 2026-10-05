"""DEM-anchored fusion: DEM-consistent at DEM scale, model detail within cells."""

import numpy as np
import pytest

from depthwizard.calibration.apply import apply_calibration
from depthwizard.calibration.fusion import box_mean, dem_anchored_calibration, dem_pixels_in_image
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.errors import CalibrationError

TARGET = ElevationSemantics.ABSOLUTE_ELEVATION_DSM


def _scene(seed: int = 0, size: int = 90, k: int = 9):
    rng = np.random.default_rng(seed)
    rows, cols = np.mgrid[0:size, 0:size]
    terrain = 300.0 + 0.4 * rows + 0.2 * cols  # hillside the model cannot see
    buildings = np.zeros((size, size))
    for _ in range(40):
        r, c = rng.integers(0, size - 6, 2)
        buildings[r : r + rng.integers(3, 12), c : c + rng.integers(3, 12)] = rng.uniform(5, 30)
    truth = terrain + buildings
    # "DEM": truth averaged over k x k cells (what a 30 m DEM sees), re-expanded.
    dem = box_mean(truth, np.ones_like(truth, dtype=bool), k)
    relative = 0.02 * buildings + 1.0  # model sees structure only, arbitrary scale
    return truth, dem, relative


def test_flat_relative_gives_pure_dem() -> None:
    _, dem, _ = _scene()
    rel = np.ones_like(dem)
    valid = np.ones_like(dem, dtype=bool)
    cal, notes = dem_anchored_calibration(
        rel, valid, dem, valid, 9, reference_id="dem", target=TARGET, source_checksum=None
    )
    out = np.asarray(apply_calibration(tuple(rel.ravel()), cal)).reshape(dem.shape)
    assert np.allclose(out, dem)
    assert cal.scale == 0.0 and notes


def test_fusion_adds_structure_and_stays_dem_consistent() -> None:
    truth, dem, rel = _scene()
    valid = np.ones_like(dem, dtype=bool)
    cal, _ = dem_anchored_calibration(
        rel, valid, dem, valid, 9, reference_id="dem", target=TARGET, source_checksum=None
    )
    assert cal.scale > 0
    out = np.asarray(apply_calibration(tuple(rel.ravel()), cal)).reshape(dem.shape)
    # Detail added on top of the DEM moves the product toward the truth...
    assert np.sqrt(np.mean((out - truth) ** 2)) < np.sqrt(np.mean((dem - truth) ** 2))
    # ...while the DEM-scale mean is preserved (agreement with the reference DEM).
    inner = (slice(18, -18), slice(18, -18))
    assert np.abs(box_mean(out, valid, 9) - dem)[inner].mean() < 1.0


def test_fusion_is_absolute_dsm_only() -> None:
    _, dem, rel = _scene()
    valid = np.ones_like(dem, dtype=bool)
    with pytest.raises(CalibrationError, match="absolute"):
        dem_anchored_calibration(
            rel,
            valid,
            dem,
            valid,
            9,
            reference_id="d",
            target=ElevationSemantics.HEIGHT_AGL_NDSM,
            source_checksum=None,
        )


def test_dem_footprint_in_image_pixels_is_odd() -> None:
    assert dem_pixels_in_image(30.0, 0.6) == 51
    assert dem_pixels_in_image(30.0, 2.0) == 15
    assert dem_pixels_in_image(30.0, 30.0) == 1
