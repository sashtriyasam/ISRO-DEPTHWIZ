"""Harness guarantees: splits, alignment, provenance, size, smoke."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from depthwizard.evaluation.alignment import check_pixel_compatibility
from depthwizard.evaluation.protocols import control_stride_split
from depthwizard.evaluation.smoke import run_smoke


def test_split_is_disjoint_and_complete() -> None:
    """Control and evaluation masks partition the valid set exactly."""
    valid = np.ones((4, 4), dtype=bool)
    valid[0, 0] = False
    control, evaluation = control_stride_split((4, 4), valid, stride=4)
    assert not (control & evaluation).any()
    assert ((control | evaluation) == valid).all()
    assert int(control.sum()) == 3
    assert int(evaluation.sum()) == 12


def test_split_rejects_bad_stride() -> None:
    """Stride 1 would leave no held-out pixels: refused."""
    with pytest.raises(ValueError, match="stride"):
        control_stride_split((4, 4), np.ones((4, 4), dtype=bool), stride=1)


def test_alignment_native_pixel() -> None:
    """Matching pixel grids pass without resampling."""
    report = check_pixel_compatibility((4, 4), (4, 4))
    assert report.method == "native-pixel"
    assert report.resampled is False


def test_alignment_shape_mismatch_refused() -> None:
    """Differing pixel grids are refused, never silently compared."""
    with pytest.raises(ValueError, match="GRID_MISMATCH"):
        check_pixel_compatibility((4, 4), (8, 8))


def test_alignment_crs_mismatch_refused() -> None:
    """Mixed CRS presence is refused without an explicit step."""
    with pytest.raises(ValueError, match="GRID_MISMATCH"):
        check_pixel_compatibility((4, 4), (4, 4), pred_crs=None, ref_crs="EPSG:32643")
    with pytest.raises(ValueError, match="GRID_MISMATCH"):
        check_pixel_compatibility((4, 4), (4, 4), pred_crs="EPSG:32643", ref_crs="EPSG:4326")


def test_smoke_has_exact_zero_error() -> None:
    """The affine fixture scores (approximately) zero held-out error."""
    result, calibrated, reference = run_smoke()
    assert result.metrics.mae == pytest.approx(0.0, abs=1e-9)
    assert result.metrics.rmse == pytest.approx(0.0, abs=1e-9)
    assert result.metrics.r_squared == pytest.approx(1.0)
    assert result.calibration_scale == pytest.approx(2.5)
    assert result.calibration_offset == pytest.approx(10.0)
    assert result.metrics.coverage_fraction == pytest.approx(12 / 16)
    assert calibrated.shape == reference.shape


def test_smoke_provenance_preserved() -> None:
    """Fixture results carry dataset/model/calibration identity."""
    result, _, _ = run_smoke()
    assert result.sample_id == "smoke-4x4"
    assert result.dataset_name == "smoke"
    assert result.model_name == "smoke-backend"
    assert result.reference_units == "meters"
    assert result.units == "meters"
    assert result.calibration_plan.protocol == "control-stride"
    assert result.alignment.method == "native-pixel"


def test_result_serializes_small() -> None:
    """Summaries stay inspection-sized (no arrays, no dumps)."""
    result, _, _ = run_smoke()
    text = result.model_dump_json()
    assert len(text) < 8192
    document = json.loads(text)
    assert document["metrics"]["valid_pixels"] == 12
    assert "depth_values" not in text


def test_no_network_in_evaluation() -> None:
    """Ordinary evaluation code performs no network access."""
    banned = (
        "import socket",
        "import requests",
        "urllib",
        "hf_hub_download",
        "snapshot_download",
        "from_pretrained",
        "torch.hub",
        "urlopen",
    )
    offenders = []
    for path in Path("src/depthwizard/evaluation").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for marker in banned:
            if marker in text:
                offenders.append(f"{path}:{marker}")
    assert offenders == []
