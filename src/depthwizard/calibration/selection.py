"""Calibration provider selection for desktop/service entry points.

One place decides which calibration source backs a metric run:

* a reference path (DEM GeoTIFF or GCP CSV) selects the production
  ``FileBasedCalibrationProvider``;
* otherwise the deterministic dev provider is used **only** when
  ``DW_DEV_CALIBRATION=1`` is set explicitly (test suites, development);
* otherwise metric output is refused: no reference means no metres.

The dev provider fits ``reference = 2.5 * predicted + 10`` and labels
its results ``synthetic-dev-ref`` so it can never pass as real data.
"""

from __future__ import annotations

import os

from depthwizard.calibration.calibrator import (
    Calibrator,
    HuberScaleOffsetCalibrator,
    PiecewiseLinearCalibrator,
    ScaleOffsetCalibrator,
)
from depthwizard.calibration.models import (
    CalibrationMethod,
    CalibrationResult,
    CalibrationSamples,
)
from depthwizard.calibration.provider import FileBasedCalibrationProvider
from depthwizard.contracts.artifacts import DepthResult
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.errors import CalibrationError
from depthwizard.ingestion.models import InputInspection

#: Environment flag enabling the synthetic dev calibration (never set by the app).
DEV_CALIBRATION_ENV = "DW_DEV_CALIBRATION"

#: Reference id stamped on every synthetic dev calibration.
DEV_REFERENCE_ID = "synthetic-dev-ref"

MISSING_REFERENCE_MESSAGE = (
    "Metric output requires a calibration reference (DEM GeoTIFF or GCP CSV); "
    "none was provided. Run in relative mode for uncalibrated imagery."
)


def make_calibrator(method: CalibrationMethod | str) -> Calibrator:
    """Build the calibrator implementing ``method`` (unknown methods raise)."""
    try:
        resolved = CalibrationMethod(method)
    except ValueError:
        supported = ", ".join(m.value for m in CalibrationMethod)
        raise CalibrationError(
            f"unsupported calibration method: {method!r} (supported: {supported})"
        ) from None
    if resolved is CalibrationMethod.SCALE_OFFSET_HUBER:
        return HuberScaleOffsetCalibrator()
    if resolved is CalibrationMethod.PIECEWISE_LINEAR:
        return PiecewiseLinearCalibrator()
    return ScaleOffsetCalibrator()


def dev_calibration_enabled() -> bool:
    """Whether the synthetic dev calibration was explicitly enabled."""
    return os.environ.get(DEV_CALIBRATION_ENV) == "1"


class DevCalibrationProvider:
    """Deterministic synthetic calibration (test/dev infrastructure only)."""

    def __init__(
        self,
        target: ElevationSemantics,
        method: CalibrationMethod | str = CalibrationMethod.SCALE_OFFSET,
    ) -> None:
        """Bind target semantics and fitting method."""
        self._target = target
        self._calibrator = make_calibrator(method)

    @property
    def name(self) -> str:
        """Stable provider name for run metadata."""
        return "synthetic-dev-provider"

    def calibrate(self, depth_result: DepthResult) -> CalibrationResult:
        """Fit the synthetic reference rule against the actual depth values."""
        predicted = depth_result.depth_values
        samples = CalibrationSamples(
            predicted_values=predicted,
            reference_values=tuple(2.5 * value + 10.0 for value in predicted),
            valid_mask=depth_result.valid_mask,
            reference_id=DEV_REFERENCE_ID,
            reference_units="meters",
            target_semantics=self._target,
            source_checksum=depth_result.provenance.input_checksum,
        )
        return self._calibrator.calibrate(samples)


class MissingReferenceProvider:
    """Refuses metric calibration when no reference source exists."""

    @property
    def name(self) -> str:
        """Stable provider name for run metadata."""
        return "missing-reference"

    def calibrate(self, depth_result: DepthResult) -> CalibrationResult:
        """Always refuse: metric values need reference evidence."""
        raise CalibrationError(MISSING_REFERENCE_MESSAGE)


CalibrationSource = FileBasedCalibrationProvider | DevCalibrationProvider | MissingReferenceProvider


#: Below this R² the reference explains too little variance for the metric
#: heights to be trusted; results are still produced but flagged.
LOW_FIT_R_SQUARED = 0.25


def fit_quality_warnings(result: CalibrationResult) -> list[str]:
    """Human-readable warnings for weak calibration fits (empty when fine)."""
    if result.r_squared >= LOW_FIT_R_SQUARED:
        return []
    explained = max(result.r_squared, 0.0) * 100.0
    return [
        f"Weak calibration: the depth model explains {explained:.0f}% of the "
        f"reference variance (R² {result.r_squared:.2f}, RMSE {result.rmse:.2f} m over "
        f"{result.valid_samples} samples). Metric heights are unreliable."
    ]


def select_calibration_provider(
    reference_path: str | None,
    target: ElevationSemantics,
    method: CalibrationMethod | str = CalibrationMethod.SCALE_OFFSET,
) -> CalibrationSource:
    """Pick the calibration source for one metric run (see module doc)."""
    calibrator = make_calibrator(method)
    if reference_path:
        return FileBasedCalibrationProvider(
            reference_path=reference_path, target=target, calibrator=calibrator
        )
    if dev_calibration_enabled():
        return DevCalibrationProvider(target, method)
    return MissingReferenceProvider()


def calibrate_with(
    provider: CalibrationSource,
    inspection: InputInspection,
    depth_result: DepthResult,
) -> CalibrationResult:
    """Run ``prepare`` (when supported) then ``calibrate`` like the pipeline does."""
    if isinstance(provider, FileBasedCalibrationProvider):
        provider.prepare(inspection)
    return provider.calibrate(depth_result)
