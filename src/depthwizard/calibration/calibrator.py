"""Affine scale+offset calibration (ordinary least squares, stdlib only).

Fits ``reference = scale * predicted + offset`` with closed-form OLS
using ``math.fsum`` compensated summation: deterministic, transparent
and dependency-light. NumPy/SciPy/scikit-learn (present in the dev
environment) were evaluated and rejected for this milestone - normal
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
#: residual degrees of freedom, so RMSE/MAE/max/R2 would be vacuous.
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


class HuberScaleOffsetCalibrator:
    @property
    def method(self) -> CalibrationMethod:
        return CalibrationMethod.SCALE_OFFSET_HUBER

    def calibrate(self, samples: CalibrationSamples) -> CalibrationResult:
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
        ols = ScaleOffsetCalibrator().calibrate(samples)
        scale = ols.scale
        offset = ols.offset
        residuals = [y - (scale * x + offset) for x, y in pairs]
        abs_res = sorted(abs(r) for r in residuals)
        median_abs = (
            abs_res[count // 2]
            if count % 2 == 1
            else (abs_res[count // 2 - 1] + abs_res[count // 2]) / 2.0
        )
        mad = max(median_abs, 1e-12)
        delta = 1.345 * mad
        for _ in range(10):
            residuals = [y - (scale * x + offset) for x, y in pairs]
            weights = [1.0 if abs(r) <= delta else delta / abs(r) for r in residuals]
            sum_w = math.fsum(weights)
            if sum_w <= 0:
                break
            x_bar = math.fsum(w * x for w, x in zip(weights, xs, strict=False)) / sum_w
            y_bar = math.fsum(w * y for w, y in zip(weights, ys, strict=False)) / sum_w
            s_xx = math.fsum(w * (x - x_bar) ** 2 for w, x in zip(weights, xs, strict=False))
            if s_xx <= 0:
                break
            s_xy = math.fsum(
                w * (x - x_bar) * (y - y_bar) for w, (x, y) in zip(weights, pairs, strict=False)
            )
            new_scale = s_xy / s_xx
            new_offset = y_bar - new_scale * x_bar
            if abs(new_scale - scale) < 1e-12 and abs(new_offset - offset) < 1e-12:
                scale = new_scale
                offset = new_offset
                break
            scale = new_scale
            offset = new_offset
        residuals = [y - (scale * x + offset) for x, y in pairs]
        ss_res = math.fsum(r * r for r in residuals)
        rmse = math.sqrt(ss_res / count)
        mae = math.fsum(abs(r) for r in residuals) / count
        max_abs = max(abs(r) for r in residuals)
        ss_tot = math.fsum((y - y_bar) ** 2 for y in ys)
        r_squared = 1.0 if ss_res == 0.0 else (1.0 - ss_res / ss_tot if ss_tot != 0.0 else 0.0)
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


class PiecewiseLinearCalibrator:
    def __init__(self, knots: int = 5) -> None:
        self._knots = max(3, int(knots))

    @property
    def method(self) -> CalibrationMethod:
        return CalibrationMethod.PIECEWISE_LINEAR

    def calibrate(self, samples: CalibrationSamples) -> CalibrationResult:
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
        [x for x, _ in pairs]
        ys = [y for _, y in pairs]
        sorted_pairs = sorted(pairs, key=lambda p: p[0])
        sorted_xs = [p[0] for p in sorted_pairs]
        sorted_ys = [p[1] for p in sorted_pairs]
        n = len(sorted_xs)
        k = self._knots
        knot_indices = [int(round(j * (n - 1) / (k - 1))) for j in range(k)]
        knot_xs = [sorted_xs[i] for i in knot_indices]
        piecewise: list[tuple[float, float, float]] = []
        for i in range(k - 1):
            x0, x1 = knot_xs[i], knot_xs[i + 1]
            interval_xs: list[float] = []
            interval_ys: list[float] = []
            for x, y in sorted_pairs:
                if x0 <= x <= x1:
                    interval_xs.append(x)
                    interval_ys.append(y)
            if len(interval_xs) < 2:
                interval_xs = [x0, x1]
                interval_ys = [
                    sorted_ys[knot_indices[i]],
                    sorted_ys[min(knot_indices[i + 1], n - 1)],
                ]
            m = len(interval_xs)
            x_bar = math.fsum(interval_xs) / m
            y_bar = math.fsum(interval_ys) / m
            s_xx = math.fsum((x - x_bar) ** 2 for x in interval_xs)
            if s_xx <= 0:
                scale = 1.0
                offset = y_bar - x_bar
            else:
                s_xy = math.fsum(
                    (x - x_bar) * (y - y_bar)
                    for x, y in zip(interval_xs, interval_ys, strict=False)
                )
                scale = s_xy / s_xx
                offset = y_bar - scale * x_bar
            piecewise.append((x0, scale, offset))

        def predict(x: float) -> float:
            for i in range(len(piecewise) - 1):
                if piecewise[i][0] <= x <= piecewise[i + 1][0]:
                    return piecewise[i][1] * x + piecewise[i][2]
            if x < piecewise[0][0]:
                return piecewise[0][1] * x + piecewise[0][2]
            last = piecewise[-1]
            return last[1] * x + last[2]

        residuals = [y - predict(x) for x, y in pairs]
        ss_res = math.fsum(r * r for r in residuals)
        rmse = math.sqrt(ss_res / count)
        mae = math.fsum(abs(r) for r in residuals) / count
        max_abs = max(abs(r) for r in residuals)
        ss_tot = math.fsum((y - y_bar) ** 2 for y in ys)
        r_squared = 1.0 if ss_res == 0.0 else (1.0 - ss_res / ss_tot if ss_tot != 0.0 else 0.0)
        return CalibrationResult(
            method=self.method,
            scale=piecewise[0][1],
            offset=piecewise[0][2],
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
            piecewise_params=tuple(piecewise),
        )
