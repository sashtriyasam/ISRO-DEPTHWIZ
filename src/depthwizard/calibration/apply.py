"""Pure application of a fitted calibration (no I/O, no mutation)."""

from __future__ import annotations

import math
from collections.abc import Sequence

from depthwizard.calibration.models import CalibrationResult
from depthwizard.errors import CalibrationError


def apply_calibration(values: Sequence[float], calibration: CalibrationResult) -> tuple[float, ...]:
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
    outputs: list[float] = []
    for index, value in enumerate(inputs):
        if not math.isfinite(value):
            raise CalibrationError(f"non-finite input value at index {index}: {value!r}")
        calibrated = calibration.scale * value + calibration.offset
        if not math.isfinite(calibrated):
            raise CalibrationError(
                f"non-finite calibrated value at index {index} "
                f"(scale={calibration.scale!r}, offset={calibration.offset!r})"
            )
        outputs.append(calibrated)
    return tuple(outputs)
