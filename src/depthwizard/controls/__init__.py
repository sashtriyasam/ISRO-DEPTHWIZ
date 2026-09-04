"""Scientifically valid reference-control pairing (no fitting here).

Combines relative predictions with explicit surface controls and DEM
terrain into auditable calibration references. Terrain is ground —
never surface; the DEM never becomes the calibration target.
"""

from depthwizard.controls.build import (
    build_calibration_samples,
    build_reference_control,
)
from depthwizard.controls.models import (
    CoordinateSpace,
    ReferenceControlPoint,
    SurfaceElevationControl,
)

__all__ = [
    "CoordinateSpace",
    "ReferenceControlPoint",
    "SurfaceElevationControl",
    "build_calibration_samples",
    "build_reference_control",
]
