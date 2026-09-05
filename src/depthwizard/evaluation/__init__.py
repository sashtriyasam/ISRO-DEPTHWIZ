"""Canonical scientific evaluation harness (measurement, never training).

Measures the existing pipeline on labelled/reference terrain: relative
prediction plus explicit calibration controls produce a metric product
that is compared pixelwise against an independent reference. Raw
relative depth is never compared to metric elevation.
"""

from depthwizard.evaluation.alignment import (
    AlignmentReport,
    check_pixel_compatibility,
)
from depthwizard.evaluation.datasets import (
    EvaluationDataset,
    EvaluationSample,
    GamusDataset,
    ReferenceInfo,
)
from depthwizard.evaluation.metrics import (
    MetricSummary,
    PooledAccumulator,
    compute_metrics,
    pool_metric_summaries,
)
from depthwizard.evaluation.protocols import (
    CalibrationPlan,
    control_stride_split,
    fit_controls,
)
from depthwizard.evaluation.results import (
    EvaluationResult,
    EvaluationRun,
)
from depthwizard.evaluation.resume import (
    load_record,
    load_resume_records,
    record_path,
    restore_accumulator,
    run_identity,
    save_record,
    snapshot_accumulator,
)
from depthwizard.evaluation.runner import (
    evaluate_run,
    evaluate_sample,
    run_sample,
    select_samples,
)
from depthwizard.evaluation.significance import (
    DEFAULT_CONFIDENCE,
    DEFAULT_RESAMPLES,
    DEFAULT_SEED,
    MIN_SAMPLES_FOR_INFERENCE,
    GroupComparison,
    GroupInterval,
    bootstrap_mean_interval,
    compare_groups,
)
from depthwizard.evaluation.smoke import (
    run_smoke,
    smoke_loaded_sample,
    smoke_reference,
    smoke_relative,
    smoke_result,
)

__all__ = [
    "AlignmentReport",
    "CalibrationPlan",
    "DEFAULT_CONFIDENCE",
    "DEFAULT_RESAMPLES",
    "DEFAULT_SEED",
    "EvaluationDataset",
    "EvaluationResult",
    "EvaluationRun",
    "EvaluationSample",
    "GamusDataset",
    "GroupComparison",
    "GroupInterval",
    "MIN_SAMPLES_FOR_INFERENCE",
    "MetricSummary",
    "PooledAccumulator",
    "ReferenceInfo",
    "bootstrap_mean_interval",
    "check_pixel_compatibility",
    "compare_groups",
    "compute_metrics",
    "control_stride_split",
    "evaluate_run",
    "evaluate_sample",
    "fit_controls",
    "load_record",
    "load_resume_records",
    "pool_metric_summaries",
    "record_path",
    "restore_accumulator",
    "run_identity",
    "run_sample",
    "save_record",
    "select_samples",
    "snapshot_accumulator",
    "run_smoke",
    "smoke_loaded_sample",
    "smoke_reference",
    "smoke_relative",
    "smoke_result",
]
