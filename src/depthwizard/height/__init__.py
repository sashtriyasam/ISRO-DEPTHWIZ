"""Scientific height/elevation semantics (meaning, not storage).

Consumes ``DepthResult`` (RELATIVE) plus a validated
``CalibrationResult`` to produce ``ScientificHeightProduct`` values in
explicit metres with declared AGL or absolute-elevation meaning.
Calibration is mandatory; the source ``DepthResult`` is never mutated.
"""

from depthwizard.height.factory import create_scientific_height_product
from depthwizard.height.product import ScientificHeightProduct

__all__ = [
    "ScientificHeightProduct",
    "create_scientific_height_product",
]
