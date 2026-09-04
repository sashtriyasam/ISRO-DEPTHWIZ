"""Canonical backend-to-desktop integration boundary (no science here).

Converts validated scientific artifacts into the JSON-safe transport
shapes the desktop consumes. The scientific Python contracts stay
canonical; this layer only translates, never recalibrates,
rerasterizes, remeshes, reprojects or reinterprets.
"""

from depthwizard.integration.adapt import (
    bundle_from_pipeline,
    calibration_to_transport,
    depth_to_transport,
    dsm_to_transport,
    mesh_to_transport,
    terrain_product,
)
from depthwizard.integration.transport import (
    TransportBundle,
    TransportCalibrationResult,
    TransportDepthResult,
    TransportDsm,
    TransportFailure,
    TransportMesh,
    TransportProvenance,
    TransportTerrainProduct,
)
from depthwizard.integration.wire import (
    is_json_safe,
    terrain_product_from_json,
    to_json_text,
)

__all__ = [
    "TransportBundle",
    "TransportCalibrationResult",
    "TransportDepthResult",
    "TransportDsm",
    "TransportFailure",
    "TransportMesh",
    "TransportProvenance",
    "TransportTerrainProduct",
    "bundle_from_pipeline",
    "calibration_to_transport",
    "depth_to_transport",
    "dsm_to_transport",
    "is_json_safe",
    "mesh_to_transport",
    "terrain_product",
    "terrain_product_from_json",
    "to_json_text",
]
