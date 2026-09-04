"""Scale-aware evaluation for frozen relative-depth baselines (M3).

Scientific protocol (NOT production calibration — see Rule E):

    1. Build a deterministic mask: finite prediction AND finite GAMUS target.
       Negative heights are KEPT (M2: -5.0 is a sentinel candidate, not a
       confirmed nodata convention). No target clipping anywhere.
    2. Fit a per-image affine map `aligned = a * prediction + b` by closed-form
       least squares on masked pixels of THAT image only. No cross-image
       leakage: parameters never transfer between samples or splits.
    3. Report MAE/RMSE on the ALIGNED prediction plus Pearson/Spearman
       correlations (scale-invariant structural measures).

What is deliberately NOT exported: any MAE/RMSE between the RAW relative
prediction and meter targets (Rule F). `raw_*` fields carry distribution
statistics only (min/max/mean/std), never error-vs-target numbers.
"""

from depthwizard.eval.alignment import (
    affine_fit,
    apply_affine,
    build_mask,
    evaluate_sample,
    mae,
    pearson,
    rmse,
    spearman,
)

__all__ = [
    "affine_fit",
    "apply_affine",
    "build_mask",
    "evaluate_sample",
    "mae",
    "pearson",
    "rmse",
    "spearman",
]
