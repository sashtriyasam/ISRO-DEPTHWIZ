"""Scale-out guarantees: selection, resume, pooling, accounting, memory."""

from __future__ import annotations

import numpy as np
import pytest

from depthwizard.evaluation.datasets import EvaluationSample
from depthwizard.evaluation.metrics import PooledAccumulator, compute_metrics
from depthwizard.evaluation.resume import (
    load_resume_records,
    restore_accumulator,
    run_identity,
    save_record,
    snapshot_accumulator,
)
from depthwizard.evaluation.runner import evaluate_run, select_samples
from depthwizard.evaluation.smoke import run_smoke


def _sample(sample_id: str) -> EvaluationSample:
    return EvaluationSample(
        sample_id=sample_id,
        dataset_name="smoke",
        split="smoke",
        image_path=f"{sample_id}.png",
        reference_path=f"{sample_id}.npy",
    )


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def test_selection_is_deterministic_slice() -> None:
    """max-samples/offset slice manifest order without score knowledge."""
    samples = [_sample(f"s-{index:02d}") for index in range(10)]
    selected = select_samples(samples, max_samples=4, offset=2)
    assert [sample.sample_id for sample in selected] == ["s-02", "s-03", "s-04", "s-05"]
    assert [sample.sample_id for sample in select_samples(samples)] == [
        sample.sample_id for sample in samples
    ]


def test_selection_rejects_bad_bounds() -> None:
    """Nonsense bounds fail instead of silently selecting nothing."""
    samples = [_sample("s-00")]
    with pytest.raises(ValueError, match="max_samples"):
        select_samples(samples, max_samples=0)
    with pytest.raises(ValueError, match="offset"):
        select_samples(samples, offset=-1)


# ---------------------------------------------------------------------------
# Accumulator math vs brute force
# ---------------------------------------------------------------------------


def test_accumulator_matches_brute_force() -> None:
    """Scalar pooling equals concatenated scoring exactly."""
    rng = np.random.default_rng(26175)
    accumulator = PooledAccumulator()
    predictions, references = [], []
    for _ in range(3):
        pred = rng.normal(0, 5, size=97)
        ref = rng.normal(0, 5, size=97)
        accumulator.add(pred - ref, ref)
        predictions.append(pred)
        references.append(ref)
    pooled = accumulator.summary()
    brute = compute_metrics(np.concatenate(predictions), np.concatenate(references))
    assert pooled["mae"] == pytest.approx(brute.mae)
    assert pooled["rmse"] == pytest.approx(brute.rmse)
    assert pooled["r_squared"] == pytest.approx(brute.r_squared)
    assert pooled["count"] == pytest.approx(291.0)


def test_accumulator_ignores_nonfinite() -> None:
    """Non-finite pairs never enter the sums."""
    accumulator = PooledAccumulator()
    accumulator.add(np.array([0.0, float("nan"), float("inf")]), np.array([1.0, 2.0, 3.0]))
    assert accumulator.count == 1
    assert accumulator.summary()["mae"] == pytest.approx(0.0)


def test_accumulator_empty_is_error() -> None:
    """Empty accumulators raise instead of returning vacuous zeros."""
    with pytest.raises(ValueError, match="NO_VALID_PIXELS"):
        PooledAccumulator().summary()


def test_evaluate_run_accepts_accumulator() -> None:
    """Run aggregation consumes accumulator summaries (memory-safe path)."""
    result, calibrated, reference = run_smoke()
    accumulator = PooledAccumulator()
    accumulator.add(calibrated - reference, reference)
    run = evaluate_run(
        [result],
        pooled=accumulator.summary(),
        requested_samples=1,
        failures=[],
        timing_seconds={"total_seconds": 1.5},
    )
    assert run.pooled_mae == pytest.approx(result.metrics.mae)
    assert run.requested_samples == 1
    assert run.completed_samples == 1
    assert run.failed_samples == 0
    assert run.timing_seconds["total_seconds"] == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# Resume
# ---------------------------------------------------------------------------


def test_resume_reuses_matching_identity(tmp_path) -> None:
    """Identical identity reloads the record without re-inference."""
    result, _, _ = run_smoke()
    identity = run_identity(
        "m",
        "smoke-backend",
        None,
        "control-stride",
        "native-pixel",
        "r",
        "smoke",
        "smoke",
        4,
        "height_agl_ndsm",
    )
    save_record(
        tmp_path,
        result.sample_id,
        result,
        identity,
        {
            "count": 1.0,
            "sum_abs": 0.0,
            "sum_sq_err": 0.0,
            "sum_y": 0.0,
            "sum_y2": 0.0,
            "max_abs": 0.0,
        },
    )
    records = load_resume_records(tmp_path, [result.sample_id, "missing"], identity)
    assert set(records) == {result.sample_id}
    loaded, snapshot = records[result.sample_id]
    assert loaded == result
    assert snapshot["count"] == pytest.approx(1.0)


def test_resume_rejects_changed_identity(tmp_path) -> None:
    """Any identity change forces re-evaluation (never silent reuse)."""
    result, _, _ = run_smoke()
    identity = run_identity(
        "m",
        "smoke-backend",
        None,
        "control-stride",
        "native-pixel",
        "r",
        "smoke",
        "smoke",
        4,
        "height_agl_ndsm",
    )
    save_record(tmp_path, result.sample_id, result, identity)
    changed = dict(identity, stride=16)
    assert load_resume_records(tmp_path, [result.sample_id], changed) == {}
    # Records without accumulator snapshots cannot rebuild pooled metrics.
    assert load_resume_records(tmp_path, [result.sample_id], identity) == {}


def test_resume_restores_exact_pooling() -> None:
    """Snapshots rebuild the accumulator bit-for-bit."""
    first, _, _ = run_smoke()
    accumulator = PooledAccumulator()
    snapshot = {
        "count": 12.0,
        "sum_abs": 0.0,
        "sum_sq_err": 0.0,
        "sum_y": 90.0,
        "sum_y2": 1240.0,
        "max_abs": 0.0,
    }
    restore_accumulator(accumulator, snapshot)
    assert accumulator.summary()["mae"] == pytest.approx(0.0)
    assert accumulator.summary()["count"] == pytest.approx(12.0)
    assert first.metrics.valid_pixels == 12


def test_snapshot_roundtrip() -> None:
    """Snapshot/restore preserves every scalar."""
    errors = np.array([1.0, -2.0, 3.0])
    references = np.array([10.0, 20.0, 30.0])
    accumulator = PooledAccumulator()
    snapshot = snapshot_accumulator(accumulator, errors, references)
    restored = PooledAccumulator()
    restore_accumulator(restored, snapshot)
    assert restored.summary() == accumulator_summary_via_direct(errors, references)


def accumulator_summary_via_direct(errors: np.ndarray, references: np.ndarray) -> dict:
    """Reference computation for the roundtrip test."""
    direct = PooledAccumulator()
    direct.add(errors, references)
    return direct.summary()


# ---------------------------------------------------------------------------
# Failure accounting + timings + backend agnosticism
# ---------------------------------------------------------------------------


def test_failure_accounting_counts() -> None:
    """Requested/completed/failed stay consistent."""
    result, _, _ = run_smoke()
    run = evaluate_run(
        [result],
        pooled={"mae": 0.0, "rmse": 0.0, "r_squared": 1.0},
        requested_samples=3,
        failures=[
            {"sample_id": "s-1", "code": "GRID_MISMATCH", "message": "x"},
            {"sample_id": "s-2", "code": "NO_VALID_PIXELS", "message": "y"},
        ],
    )
    assert run.requested_samples == 3
    assert run.completed_samples == 1
    assert run.failed_samples == 2
    assert len(run.failures) == 2


def test_timings_survive_serialization() -> None:
    """Per-sample timings round-trip through the frozen contract."""
    result, _, _ = run_smoke()
    assert set(result.timings) == {
        "inference_seconds",
        "calibration_seconds",
        "metric_seconds",
        "total_seconds",
    }
    assert all(value >= 0 for value in result.timings.values())
    assert result.model_dump(mode="json")["timings"] == result.timings


def test_backend_agnostic_shapes() -> None:
    """Synthetic and smoke backends both fit the evaluator."""
    import numpy as np

    from depthwizard.backends.synthetic import SyntheticDepthBackend
    from depthwizard.contracts.semantics import ElevationSemantics
    from depthwizard.evaluation.datasets import LoadedSample, ReferenceInfo
    from depthwizard.evaluation.runner import evaluate_sample
    from depthwizard.evaluation.smoke import smoke_loaded_sample

    rgb = np.zeros((8, 8, 3), dtype=np.uint8)
    reference = np.arange(64, dtype=np.float64).reshape(8, 8)
    loaded = LoadedSample(
        sample=smoke_loaded_sample().sample,
        image_rgb=np.ascontiguousarray(rgb),
        reference=ReferenceInfo(
            values=np.ascontiguousarray(reference),
            width=8,
            height=8,
            units="meters",
            semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
            crs=None,
            valid_mask=np.ones_like(reference, dtype=bool),
        ),
    )
    # Stride 7 (not 8) so controls spread across the analytic pattern.
    synthetic = evaluate_sample(loaded, SyntheticDepthBackend(), stride=7)
    assert synthetic.model_name == "synthetic-depth"
    assert synthetic.metrics.coverage_fraction > 0
    assert synthetic.metrics.units == "meters"


def test_determinism_same_fixture_same_summary() -> None:
    """Same fixture twice yields identical summaries (timings excluded)."""
    from depthwizard.evaluation.smoke import smoke_result

    first = smoke_result().model_dump(exclude={"timings"})
    second = smoke_result().model_dump(exclude={"timings"})
    assert first == second
