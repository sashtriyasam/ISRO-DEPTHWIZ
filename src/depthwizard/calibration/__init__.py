"""Independent deterministic calibration engine (affine scale + offset).

Maps scale-ambiguous relative values onto a metric reference via
``reference = scale * predicted + offset``. No rasters, no models,
no desktop knowledge. Calibration is not elevation semantics: the
later height-semantics layer consumes ``CalibrationResult`` to build
scientific products.
"""

from depthwizard.calibration.apply import apply_calibration
from depthwizard.calibration.calibrator import (
    MIN_VALID_SAMPLES,
    Calibrator,
    ScaleOffsetCalibrator,
)
from depthwizard.calibration.models import (
    CalibrationMethod,
    CalibrationResult,
    CalibrationSamples,
)

__all__ = [
    "MIN_VALID_SAMPLES",
    "CalibrationMethod",
    "CalibrationResult",
    "CalibrationSamples",
    "Calibrator",
    "ScaleOffsetCalibrator",
    "apply_calibration",
]
