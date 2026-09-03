"""Calibration sample/result contracts (immutable, tuple-based).

``CalibrationSamples`` carries already-paired scalar samples: relative
predictions plus known metric references. ``CalibrationResult`` records
the fitted affine mapping with residual evidence. Neither model reads
rasters, opens images, or knows about the desktop application.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from depthwizard.contracts.artifacts import METRIC_UNIT
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import ElevationSemantics


class CalibrationMethod(str, Enum):
    """Fitting methods actually implemented (no future-method placeholders)."""

    SCALE_OFFSET = "scale_offset"


_METRIC_TARGETS = frozenset(
    {
        ElevationSemantics.HEIGHT_AGL_NDSM,
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    }
)


class CalibrationSamples(BaseModel):
    """Paired predicted/reference samples for affine calibration.

    Structural validation happens here (lengths, identifier, metric
    units, metric target semantics). Numerical validation (finiteness,
    variance, minimum count) happens at fit time in the calibrator, so
    a deliberately masked-out non-finite point can still be excluded
    via ``valid_mask`` instead of failing construction.
    """

    model_config = ConfigDict(frozen=True)

    predicted_values: tuple[float, ...] = Field(
        min_length=1, description="Relative/scale-ambiguous predicted values."
    )
    reference_values: tuple[float, ...] = Field(
        min_length=1, description="Known metric reference values."
    )
    valid_mask: tuple[bool, ...] | None = Field(
        default=None,
        description="True marks a sample used for fitting; "
        "False excludes it (reported, never silent).",
    )
    reference_id: str = Field(min_length=1)
    reference_checksum: str | None = None
    reference_units: str = Field(description="Must be explicit metric units ('meters').")
    target_semantics: ElevationSemantics = Field(
        description="Metric meaning the reference carries "
        "(AGL/nDSM-style height or absolute elevation)."
    )
    source_input_id: str | None = None
    source_checksum: str | None = None

    @model_validator(mode="after")
    def _check_structure(self) -> CalibrationSamples:
        if len(self.predicted_values) != len(self.reference_values):
            raise ValueError(
                f"predicted ({len(self.predicted_values)}) and reference "
                f"({len(self.reference_values)}) sample counts differ"
            )
        if self.valid_mask is not None and len(self.valid_mask) != len(self.predicted_values):
            raise ValueError(
                f"valid_mask length ({len(self.valid_mask)}) must match "
                f"sample count ({len(self.predicted_values)})"
            )
        if self.reference_units != METRIC_UNIT:
            raise ValueError(
                f"calibration reference must carry explicit metric units "
                f"('{METRIC_UNIT}'); got '{self.reference_units}'"
            )
        if self.target_semantics not in _METRIC_TARGETS:
            raise ValueError(
                f"calibration target must be a metric meaning "
                f"({sorted(m.value for m in _METRIC_TARGETS)}); "
                f"got '{self.target_semantics.value}'"
            )
        return self

    @property
    def total_samples(self) -> int:
        """Number of paired samples (used + excluded)."""
        return len(self.predicted_values)

    def selected_pairs(self) -> tuple[tuple[float, float], ...]:
        """Mask-selected (predicted, reference) pairs in original order."""
        if self.valid_mask is None:
            return tuple(zip(self.predicted_values, self.reference_values, strict=True))
        return tuple(
            (x, y)
            for x, y, use in zip(
                self.predicted_values, self.reference_values, self.valid_mask, strict=True
            )
            if use
        )


class CalibrationResult(BaseModel):
    """Fitted affine mapping with residual evidence (no confidence claims).

    Residual metrics (RMSE/MAE/max/R²) are evidence of fit quality on
    the calibration samples — not model confidence, not accuracy claims.
    """

    model_config = ConfigDict(frozen=True)

    method: CalibrationMethod
    scale: float = Field(description="Multiplicative term a in y = a*x + b.")
    offset: float = Field(description="Additive term b in y = a*x + b.")
    reference_id: str
    reference_checksum: str | None = None
    reference_units: str
    target_semantics: ElevationSemantics
    total_samples: int = Field(ge=0)
    valid_samples: int = Field(ge=0)
    rmse: float = Field(ge=0, description="Root-mean-square residual on used samples.")
    mae: float = Field(ge=0, description="Mean absolute residual on used samples.")
    max_abs_residual: float = Field(ge=0)
    r_squared: float = Field(
        description="1 - SSres/SStot on used samples; 1.0/0.0 convention "
        "when the reference is constant (perfect/imperfect)."
    )
    engine_version: str
    source_input_id: str | None = None
    source_checksum: str | None = None

    @property
    def engine(self) -> str:
        """Engine/software version alias for provenance-style access."""
        return self.engine_version

    def to_provenance(self) -> ProductProvenance:
        """Build the shared provenance record for this calibration.

        Reuses :class:`ProductProvenance` instead of duplicating it:
        method, reference, (scale, offset) parameters, units, target
        meaning, engine version and source linkage. ``generated_at``
        stays None so results remain deterministic.
        """
        return ProductProvenance(
            source_input_id=self.source_input_id,
            input_checksum=self.source_checksum,
            calibration_method=self.method.value,
            calibration_reference=self.reference_id,
            calibration_params=(self.scale, self.offset),
            software_version=self.engine_version,
            generated_at=None,
            units=self.reference_units,
            semantic_meaning=self.target_semantics.value,
        )
