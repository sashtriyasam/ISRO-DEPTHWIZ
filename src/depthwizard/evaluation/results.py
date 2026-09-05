"""Frozen evaluation result contracts (summaries only, JSON-safe).

No arrays, no prediction dumps: per-sample summaries carry metric
values plus the identities needed to reproduce them; run results pool
pixelwise errors explicitly rather than averaging per-image RMSE.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from depthwizard.evaluation.alignment import AlignmentReport
from depthwizard.evaluation.metrics import MetricSummary
from depthwizard.evaluation.protocols import CalibrationPlan


class EvaluationResult(BaseModel):
    """One sample's complete evaluation record."""

    model_config = ConfigDict(frozen=True)

    sample_id: str = Field(min_length=1)
    dataset_name: str = Field(min_length=1)
    dataset_release: str | None = None
    manifest_checksum: str | None = None
    split: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    model_version: str | None = None
    checkpoint_id: str | None = None
    checkpoint_sha256: str | None = None
    upstream_revision: str | None = None
    input_checksum: str | None = None
    reference_id: str = Field(min_length=1)
    reference_checksum: str | None = None
    reference_units: str = Field(description="Evaluated reference units ('meters').")
    reference_semantics: str = Field(description="Declared reference meaning.")
    calibration_method: str = Field(min_length=1)
    calibration_scale: float
    calibration_offset: float
    calibration_rmse: float = Field(ge=0.0, description="Fit residual on controls (not accuracy).")
    calibration_r_squared: float
    calibration_controls: int = Field(ge=0)
    metrics: MetricSummary = Field(description="Held-out evaluation pixels only.")
    calibration_plan: CalibrationPlan
    alignment: AlignmentReport
    units: str = Field(description="Scored units ('meters').")
    product_semantics: str = Field(description="Calibrated product meaning.")
    device: str | None = None
    python_version: str | None = None
    engine_version: str | None = None
    repository_sha: str | None = None


class EvaluationRun(BaseModel):
    """Aggregate run result with explicit pooling rules."""

    model_config = ConfigDict(frozen=True)

    dataset_name: str = Field(min_length=1)
    dataset_release: str | None = None
    manifest_checksum: str | None = None
    split: str = Field(min_length=1)
    sample_count: int = Field(ge=0)
    total_pixels: int = Field(ge=0)
    valid_pixels: int = Field(ge=0)
    invalid_pixels: int = Field(ge=0)
    coverage_fraction: float = Field(ge=0.0, le=1.0)
    pooled_mae: float = Field(ge=0.0, description="MAE over concatenated held-out pixels.")
    pooled_rmse: float = Field(ge=0.0, description="RMSE over concatenated held-out pixels.")
    pooled_r_squared: float = Field(description="R² over concatenated held-out pixels.")
    macro: dict[str, float] = Field(
        description="Mean of per-sample summaries (typical-sample view, not primary)."
    )
    per_sample: tuple[EvaluationResult, ...] = Field(default=())
    model_name: str = Field(min_length=1)
    model_version: str | None = None
    checkpoint_id: str | None = None
    checkpoint_sha256: str | None = None
    upstream_revision: str | None = None
    calibration_protocol: str = Field(min_length=1)
    alignment_protocol: str = Field(min_length=1)
    units: str = Field(description="Scored units ('meters').")
    product_semantics: str = Field(description="Calibrated product meaning.")
    device: str | None = None
    python_version: str | None = None
    engine_version: str | None = None
    repository_sha: str | None = None
