"""Pure application of a fitted calibration (no I/O, no mutation)."""

from __future__ import annotations

import math
from collections.abc import Sequence

from depthwizard.calibration.models import CalibrationResult
from depthwizard.errors import CalibrationError


def apply_calibration(
    values: Sequence[float],
    calibration: CalibrationResult,
    piecewise_params: tuple[tuple[float, float, float], ...] | None = None,
) -> tuple[float, ...]:
    """Apply ``calibrated = scale * value + offset`` element-wise.

    Deterministic, side-effect free, cardinality preserving. Rejects
    non-finite inputs and non-finite outputs (e.g. overflow) with
    :class:`CalibrationError` naming the offending index. The input
    sequence is never mutated.
    """
    if not isinstance(calibration, CalibrationResult):
        raise TypeError(
            f"apply_calibration requires a CalibrationResult; got {type(calibration).__name__}"
        )
    try:
        inputs = [float(v) for v in values]
    except (TypeError, ValueError) as exc:
        raise CalibrationError(f"calibration input is not numeric: {exc}") from exc

    def predict(x: float) -> float:
        if piecewise_params is not None:
            for i in range(len(piecewise_params) - 1):
                if piecewise_params[i][0] <= x <= piecewise_params[i + 1][0]:
                    return piecewise_params[i][1] * x + piecewise_params[i][2]
            if x < piecewise_params[0][0]:
                return piecewise_params[0][1] * x + piecewise_params[0][2]
            last = piecewise_params[-1]
            return last[1] * x + last[2]
        return calibration.scale * x + calibration.offset

    outputs: list[float] = []
    for index, value in enumerate(inputs):
        if not math.isfinite(value):
            raise CalibrationError(f"non-finite input value at index {index}: {value!r}")
        calibrated = predict(value)
        if not math.isfinite(calibrated):
            raise CalibrationError(
                f"non-finite calibrated value at index {index} "
                f"(scale={calibration.scale!r}, offset={calibration.offset!r})"
            )
        outputs.append(calibrated)
    return tuple(outputs)
