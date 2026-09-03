"""Affine scale+offset calibration (ordinary least squares, stdlib only).

Fits ``reference = scale * predicted + offset`` with closed-form OLS
using ``math.fsum`` compensated summation: deterministic, transparent
and dependency-light. NumPy/SciPy/scikit-learn (present in the dev
environment) were evaluated and rejected for this milestone — normal
equations on small sample sets need nothing beyond exactly-rounded
sums.

``Calibrator`` is a small protocol so future robust variants (Huber,
RANSAC) can substitute without changing callers. Only
``ScaleOffsetCalibrator`` is implemented.
"""

from __future__ import annotations

import math
from typing import Protocol

from depthwizard.calibration.models import (
    CalibrationMethod,
    CalibrationResult,
    CalibrationSamples,
)
from depthwizard.errors import CalibrationError
from depthwizard.version import __version__

#: Minimum valid samples: two points determine a line but leave zero
#: residual degrees of freedom, so RMSE/MAE/max/R² would be vacuous.
#: Three gives one degree of freedom for the residual evidence to
#: mean something. No claim of scientific adequacy beyond that.
MIN_VALID_SAMPLES = 3


class Calibrator(Protocol):
    """Interface for calibration implementations (present and future)."""

    @property
    def method(self) -> CalibrationMethod:
        """The fitting method this calibrator implements."""
        ...

    def calibrate(self, samples: CalibrationSamples) -> CalibrationResult:
        """Fit the affine mapping for validated samples."""
        ...


class ScaleOffsetCalibrator:
    """Ordinary-least-squares affine calibrator. Stateless, deterministic."""

    @property
    def method(self) -> CalibrationMethod:
        """The implemented fitting method."""
        return CalibrationMethod.SCALE_OFFSET

    def calibrate(self, samples: CalibrationSamples) -> CalibrationResult:
        """Fit ``reference = scale * predicted + offset``.

        Raises :class:`CalibrationError` for too few valid samples,
        non-finite values, zero predictor variance, or non-finite fit
        results. Parameters are never rounded.
        """
        pairs = samples.selected_pairs()
        count = len(pairs)
        if count < MIN_VALID_SAMPLES:
            raise CalibrationError(
                f"affine calibration needs at least {MIN_VALID_SAMPLES} "
                f"valid samples for scale + offset with residual evidence; "
                f"got {count} (of {samples.total_samples} total)"
            )
        for index, (predicted, reference) in enumerate(pairs):
            if not math.isfinite(predicted):
                raise CalibrationError(
                    f"non-finite predicted value at sample index {index}: {predicted!r}"
                )
            if not math.isfinite(reference):
                raise CalibrationError(
                    f"non-finite reference value at sample index {index}: {reference!r}"
                )
        xs = [x for x, _ in pairs]
        ys = [y for _, y in pairs]
        x_bar = math.fsum(xs) / count
        y_bar = math.fsum(ys) / count
        s_xx = math.fsum((x - x_bar) ** 2 for x in xs)
        if not s_xx > 0.0:
            raise CalibrationError(
                f"degenerate predictor: {count} valid samples have zero "
                "variance (all predicted values identical); "
                "scale is undefined"
            )
        s_xy = math.fsum((x - x_bar) * (y - y_bar) for x, y in pairs)
        scale = s_xy / s_xx
        offset = y_bar - scale * x_bar
        if not math.isfinite(scale) or not math.isfinite(offset):
            raise CalibrationError(
                f"non-finite fit result: scale={scale!r}, offset={offset!r} "
                f"from {count} valid samples"
            )
        residuals = [y - (scale * x + offset) for x, y in pairs]
        ss_res = math.fsum(r * r for r in residuals)
        rmse = math.sqrt(ss_res / count)
        mae = math.fsum(abs(r) for r in residuals) / count
        max_abs = max(abs(r) for r in residuals)
        ss_tot = math.fsum((y - y_bar) ** 2 for y in ys)
        if ss_tot == 0.0:
            r_squared = 1.0 if ss_res == 0.0 else 0.0
        else:
            r_squared = 1.0 - ss_res / ss_tot
        return CalibrationResult(
            method=self.method,
            scale=scale,
            offset=offset,
            reference_id=samples.reference_id,
            reference_checksum=samples.reference_checksum,
            reference_units=samples.reference_units,
            target_semantics=samples.target_semantics,
            total_samples=samples.total_samples,
            valid_samples=count,
            rmse=rmse,
            mae=mae,
            max_abs_residual=max_abs,
            r_squared=r_squared,
            engine_version=__version__,
            source_input_id=samples.source_input_id,
            source_checksum=samples.source_checksum,
        )
