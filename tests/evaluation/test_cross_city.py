"""Cross-city guarantees: grouping, per-city pooling, manifest identity."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from depthwizard.evaluation.metrics import PooledAccumulator
from depthwizard.evaluation.runner import evaluate_run
from depthwizard.evaluation.smoke import run_smoke


def _city_result(city: str, bias: float):
    """Smoke result relabelled to a city with a shifted metric copy."""
    result, _, _ = run_smoke()
    metrics = result.metrics.model_copy(update={"mae": result.metrics.mae + bias})
    return result.model_copy(update={"city": city, "metrics": metrics})


def test_city_grouping_from_manifest_labels() -> None:
    """by_city groups follow result city labels (no invented geography)."""
    results = [_city_result("DC", 0.0), _city_result("PHL", 1.0)]
    run = evaluate_run(
        results, pooled={"mae": 0.5, "rmse": 0.5, "r_squared": 0.0}, requested_samples=2
    )
    assert set(run.by_city) == {"DC", "PHL"}
    assert run.by_city["PHL"]["mae"] == pytest.approx(run.by_city["DC"]["mae"] + 1.0)


def test_per_city_pooled_exactness() -> None:
    """Per-city pooled summaries equal accumulator math on city pairs."""
    rng = np.random.default_rng(7)
    city_accumulator = PooledAccumulator()
    errors = rng.normal(0, 2, size=50)
    references = rng.normal(10, 2, size=50)
    city_accumulator.add(errors, references)
    pooled = city_accumulator.summary()
    results = [_city_result("PHL", 0.0)]
    run = evaluate_run(
        results,
        pooled={"mae": 0.0, "rmse": 0.0, "r_squared": 0.0},
        requested_samples=1,
        by_city_pooled={"PHL": pooled},
    )
    assert run.by_city_pooled["PHL"]["mae"] == pytest.approx(pooled["mae"])
    assert run.by_city_pooled["PHL"]["count"] == pytest.approx(50.0)


def test_calibration_transfer_table() -> None:
    """Per-city calibration means derive from member results."""
    results = [_city_result("DC", 0.0), _city_result("DC", 0.0)]
    run = evaluate_run(
        results, pooled={"mae": 0.0, "rmse": 0.0, "r_squared": 1.0}, requested_samples=2
    )
    table = run.by_city_calibration["DC"]
    assert table["sample_count"] == pytest.approx(2.0)
    assert table["mean_scale"] == pytest.approx(results[0].calibration_scale)
    assert table["mean_residual_rmse"] == pytest.approx(results[0].calibration_rmse)
    assert table["control_pixels"] == pytest.approx(
        float(sum(r.calibration_plan.control_pixels for r in results))
    )


def test_cross_city_manifest_shape(tmp_path=None) -> None:
    """Cross-city manifest entries carry city labels and checksums."""
    manifest = json.loads(Path("manifests/gamus-cross-city.json").read_text())
    assert manifest["dataset"] == "gamus"
    assert "selection_rule" in manifest
    cities = {sample["source"]["city"] for sample in manifest["samples"]}
    assert cities == {"DC", "PHL"}
    for sample in manifest["samples"]:
        assert len(sample["input_checksum"]) == 64
        assert len(sample["reference_checksum"]) == 64
        assert "/" not in sample["sample_id"]
        assert not sample["image_path"].startswith(("/", "C:", "~"))


def test_result_serializes_with_city_fields() -> None:
    """City/pooled additions stay small and JSON-safe."""
    results = [_city_result("DC", 0.0)]
    run = evaluate_run(
        results,
        pooled={"mae": 0.0, "rmse": 0.0, "r_squared": 1.0},
        requested_samples=1,
        by_city_pooled={
            "DC": {"mae": 0.0, "rmse": 0.0, "r_squared": 1.0, "max_abs_error": 0.0, "count": 12.0}
        },
    )
    text = run.model_dump_json()
    assert len(text) < 16384
    assert json.loads(text)["by_city_pooled"]["DC"]["count"] == 12.0
