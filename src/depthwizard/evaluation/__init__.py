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
from depthwizard.evaluation.runner import (
    evaluate_run,
    evaluate_sample,
    run_sample,
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
    "EvaluationDataset",
    "EvaluationResult",
    "EvaluationRun",
    "EvaluationSample",
    "GamusDataset",
    "MetricSummary",
    "ReferenceInfo",
    "check_pixel_compatibility",
    "compute_metrics",
    "control_stride_split",
    "evaluate_run",
    "evaluate_sample",
    "fit_controls",
    "pool_metric_summaries",
    "run_sample",
    "run_smoke",
    "smoke_loaded_sample",
    "smoke_reference",
    "smoke_relative",
    "smoke_result",
]
