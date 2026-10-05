"""Affine scale+offset calibration (ordinary least squares, stdlib only).

Fits ``reference = scale * predicted + offset`` with closed-form OLS
using ``math.fsum`` compensated summation: deterministic, transparent
and dependency-light. NumPy/SciPy/scikit-learn (present in the dev
environment) were evaluated and rejected for this milestone - normal
equations on small sample sets need nothing beyond exactly-rounded
sums.

``Calibrator`` is a small protocol implemented by OLS, robust Huber
IRLS and a continuous piecewise-linear spline. All three share sample
validation and residual statistics (R² is always against the plain
mean of the used references).
"""

from __future__ import annotations

import math
from collections.abc import Callable
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


def _validated_pairs(samples: CalibrationSamples) -> tuple[tuple[float, float], ...]:
    """Selected pairs after the shared count and finiteness checks."""
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
    return pairs


def _weighted_line(
    pairs: tuple[tuple[float, float], ...], weights: list[float] | None = None
) -> tuple[float, float]:
    """(Weighted) least-squares line ``y = scale * x + offset``."""
    w = weights if weights is not None else [1.0] * len(pairs)
    sum_w = math.fsum(w)
    x_bar = math.fsum(wi * x for wi, (x, _) in zip(w, pairs, strict=True)) / sum_w
    y_bar = math.fsum(wi * y for wi, (_, y) in zip(w, pairs, strict=True)) / sum_w
    s_xx = math.fsum(wi * (x - x_bar) ** 2 for wi, (x, _) in zip(w, pairs, strict=True))
    if not s_xx > 0.0:
        raise CalibrationError(
            f"degenerate predictor: {len(pairs)} valid samples have zero "
            "variance (all predicted values identical); "
            "scale is undefined"
        )
    s_xy = math.fsum(wi * (x - x_bar) * (y - y_bar) for wi, (x, y) in zip(w, pairs, strict=True))
    scale = s_xy / s_xx
    offset = y_bar - scale * x_bar
    if not math.isfinite(scale) or not math.isfinite(offset):
        raise CalibrationError(
            f"non-finite fit result: scale={scale!r}, offset={offset!r} "
            f"from {len(pairs)} valid samples"
        )
    return scale, offset


def _result(
    method: CalibrationMethod,
    samples: CalibrationSamples,
    pairs: tuple[tuple[float, float], ...],
    predict: Callable[[float], float],
    scale: float,
    offset: float,
    piecewise_params: tuple[tuple[float, float, float], ...] | None = None,
) -> CalibrationResult:
    """Residual statistics on the used samples (R² against the plain mean)."""
    count = len(pairs)
    residuals = [y - predict(x) for x, y in pairs]
    ss_res = math.fsum(r * r for r in residuals)
    y_mean = math.fsum(y for _, y in pairs) / count
    ss_tot = math.fsum((y - y_mean) ** 2 for _, y in pairs)
    if ss_tot == 0.0:
        r_squared = 1.0 if ss_res == 0.0 else 0.0
    else:
        r_squared = 1.0 - ss_res / ss_tot
    return CalibrationResult(
        method=method,
        scale=scale,
        offset=offset,
        reference_id=samples.reference_id,
        reference_checksum=samples.reference_checksum,
        reference_units=samples.reference_units,
        target_semantics=samples.target_semantics,
        total_samples=samples.total_samples,
        valid_samples=count,
        rmse=math.sqrt(ss_res / count),
        mae=math.fsum(abs(r) for r in residuals) / count,
        max_abs_residual=max(abs(r) for r in residuals),
        r_squared=r_squared,
        engine_version=__version__,
        source_input_id=samples.source_input_id,
        source_checksum=samples.source_checksum,
        piecewise_params=piecewise_params,
    )


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
        pairs = _validated_pairs(samples)
        scale, offset = _weighted_line(pairs)
        return _result(self.method, samples, pairs, lambda x: scale * x + offset, scale, offset)


#: Huber tuning constant (95% efficiency under Gaussian residuals) and the
#: MAD→sigma consistency factor; δ = 1.345·σ̂ with σ̂ = 1.4826·MAD.
HUBER_K = 1.345
MAD_TO_SIGMA = 1.4826


class HuberScaleOffsetCalibrator:
    """Robust affine calibrator: Huber IRLS starting from OLS."""

    def __init__(self, max_iterations: int = 50) -> None:
        self._max_iterations = max(1, int(max_iterations))

    @property
    def method(self) -> CalibrationMethod:
        return CalibrationMethod.SCALE_OFFSET_HUBER

    def calibrate(self, samples: CalibrationSamples) -> CalibrationResult:
        pairs = _validated_pairs(samples)
        scale, offset = _weighted_line(pairs)
        for _ in range(self._max_iterations):
            residuals = [y - (scale * x + offset) for x, y in pairs]
            abs_res = sorted(abs(r) for r in residuals)
            mid = len(abs_res) // 2
            mad = abs_res[mid] if len(abs_res) % 2 == 1 else (abs_res[mid - 1] + abs_res[mid]) / 2.0
            sigma = MAD_TO_SIGMA * mad
            if not sigma > 1e-12:
                break  # (near-)exact fit: nothing to down-weight
            delta = HUBER_K * sigma
            weights = [1.0 if abs(r) <= delta else delta / abs(r) for r in residuals]
            new_scale, new_offset = _weighted_line(pairs, weights)
            converged = abs(new_scale - scale) <= 1e-12 * max(1.0, abs(scale)) and abs(
                new_offset - offset
            ) <= 1e-12 * max(1.0, abs(offset))
            scale, offset = new_scale, new_offset
            if converged:
                break
        return _result(self.method, samples, pairs, lambda x: scale * x + offset, scale, offset)


#: Fewest samples per piecewise segment (fewer would interpolate noise).
MIN_SAMPLES_PER_SEGMENT = 2


class PiecewiseLinearCalibrator:
    """Continuous piecewise-linear calibration (least-squares linear spline).

    Knots sit at sample quantiles of the predicted values; the fit is one
    joint least-squares problem over hinge functions, so neighbouring
    segments meet at every knot (no height cliffs). The segment count is
    reduced when samples are scarce; one segment equals the OLS line.
    """

    def __init__(self, knots: int = 5) -> None:
        self._knots = max(3, int(knots))

    @property
    def method(self) -> CalibrationMethod:
        return CalibrationMethod.PIECEWISE_LINEAR

    def calibrate(self, samples: CalibrationSamples) -> CalibrationResult:
        import numpy as np

        pairs = _validated_pairs(samples)
        global_scale, global_offset = _weighted_line(pairs)
        xs = np.array([x for x, _ in pairs], dtype=np.float64)
        ys = np.array([y for _, y in pairs], dtype=np.float64)
        sorted_xs = np.sort(xs)
        n = int(sorted_xs.size)
        segments = max(1, min(self._knots - 1, n // MIN_SAMPLES_PER_SEGMENT))
        knot_indices = [int(round(j * (n - 1) / segments)) for j in range(segments + 1)]
        knots = [float(v) for v in np.unique(sorted_xs[knot_indices])]
        interior = knots[1:-1]
        design = np.column_stack(
            [np.ones_like(xs), xs] + [np.maximum(0.0, xs - k) for k in interior]
        )
        coef, *_ = np.linalg.lstsq(design, ys, rcond=None)
        if not bool(np.isfinite(coef).all()):
            raise CalibrationError("piecewise fit produced non-finite coefficients")
        base_offset, base_slope = float(coef[0]), float(coef[1])
        hinge = [float(c) for c in coef[2:]]
        params: list[tuple[float, float, float]] = []
        slope, offset = base_slope, base_offset
        params.append((knots[0], slope, offset))
        for knot, c in zip(interior, hinge, strict=True):
            slope += c
            offset -= c * knot
            params.append((knot, slope, offset))
        piecewise = tuple(params)

        def predict(x: float) -> float:
            chosen = piecewise[0]
            for segment in piecewise:
                if x >= segment[0]:
                    chosen = segment
            return chosen[1] * x + chosen[2]

        return _result(
            self.method,
            samples,
            pairs,
            predict,
            # Representative global line for display only; piecewise_params
            # is the authoritative mapping (apply_calibration uses it).
            global_scale,
            global_offset,
            piecewise_params=piecewise,
        )
