"""Factory for scientific height products (validation lives here).

``create_scientific_height_product`` is the only sanctioned path from
a relative ``DepthResult`` plus a validated ``CalibrationResult`` to a
metric ``ScientificHeightProduct``. There is deliberately no
``create_product(relative_depth)`` overload: calibration is mandatory
and explicit.
"""

from __future__ import annotations

import math

from depthwizard.calibration.apply import apply_calibration
from depthwizard.calibration.models import CalibrationResult
from depthwizard.contracts.artifacts import METRIC_UNIT, DepthResult
from depthwizard.contracts.semantics import DepthScale, ElevationSemantics
from depthwizard.errors import CalibrationError
from depthwizard.height.product import ScientificHeightProduct

_RELATIVE_MEANINGS = frozenset(
    {
        ElevationSemantics.RELATIVE_DEPTH,
        ElevationSemantics.RELATIVE_SURFACE_RDSM,
    }
)

_METRIC_MEANINGS = frozenset(
    {
        ElevationSemantics.HEIGHT_AGL_NDSM,
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    }
)


def create_scientific_height_product(
    depth_result: DepthResult,
    calibration: CalibrationResult,
    target_semantics: ElevationSemantics,
) -> ScientificHeightProduct:
    """Build a metric height product from relative depth + calibration.

    The source ``DepthResult`` is never mutated. Metric meaning comes
    solely from the explicit-metre calibration reference together with
    the caller-requested target semantics, which must agree with the
    calibration's own target. Spatial metadata is preserved as-is:
    calibration changes numeric semantics, never spatial referencing.
    """
    if not isinstance(depth_result, DepthResult):
        raise TypeError(
            "create_scientific_height_product requires a DepthResult; "
            f"got {type(depth_result).__name__}"
        )
    if not isinstance(calibration, CalibrationResult):
        raise TypeError(
            "create_scientific_height_product requires a CalibrationResult; "
            f"got {type(calibration).__name__}"
        )
    if depth_result.depth_scale is not DepthScale.RELATIVE:
        raise CalibrationError(
            "height products are derived from RELATIVE depth via calibration; "
            f"this DepthResult already claims {depth_result.depth_scale.value} "
            "scale (re-calibrating metric output would be unsound)"
        )
    if depth_result.elevation_semantics not in _RELATIVE_MEANINGS:
        raise CalibrationError(
            "height products require a relative depth source; "
            f"got elevation semantics '{depth_result.elevation_semantics.value}'"
        )
    if target_semantics not in _METRIC_MEANINGS:
        raise CalibrationError(
            "requested product semantics must be a metric meaning "
            f"({sorted(m.value for m in _METRIC_MEANINGS)}); "
            f"got '{target_semantics.value}'"
        )
    if calibration.target_semantics is not target_semantics:
        raise CalibrationError(
            "calibration target semantics "
            f"('{calibration.target_semantics.value}') disagree with requested "
            f"product semantics ('{target_semantics.value}'); refusing to reinterpret"
        )
    if calibration.reference_units != METRIC_UNIT:
        raise CalibrationError(
            "metric products require an explicit-metre calibration reference; "
            f"got units '{calibration.reference_units}'"
        )
    if not math.isfinite(calibration.scale) or not math.isfinite(calibration.offset):
        raise CalibrationError(
            f"non-finite calibration parameters: scale={calibration.scale!r}, "
            f"offset={calibration.offset!r}"
        )
    depth_checksum = depth_result.provenance.input_checksum
    calibration_checksum = calibration.source_checksum
    if (
        depth_checksum is not None
        and calibration_checksum is not None
        and depth_checksum != calibration_checksum
    ):
        raise CalibrationError(
            "source linkage contradiction: depth input checksum "
            f"({depth_checksum}) differs from calibration source checksum "
            f"({calibration_checksum}); refusing to combine unrelated sources"
        )
    values = apply_calibration(depth_result.depth_values, calibration)
    source_input_id = depth_result.provenance.source_input_id or calibration.source_input_id
    source_checksum = depth_checksum or calibration_checksum
    provenance = calibration.to_provenance().model_copy(
        update={
            "model_name": depth_result.model_name,
            "model_version": depth_result.model_version,
            "checkpoint_id": depth_result.checkpoint_id,
            "source_input_id": source_input_id,
            "input_checksum": source_checksum,
            "semantic_meaning": target_semantics.value,
        }
    )
    return ScientificHeightProduct(
        values=values,
        width=depth_result.output_resolution.width,
        height=depth_result.output_resolution.height,
        units=METRIC_UNIT,
        semantics=target_semantics,
        georeferencing=depth_result.georeferencing,
        spatial=depth_result.spatial,
        depth_model_name=depth_result.model_name,
        depth_model_version=depth_result.model_version,
        depth_checkpoint_id=depth_result.checkpoint_id,
        source_input_id=source_input_id,
        source_checksum=source_checksum,
        calibration_method=calibration.method.value,
        calibration_reference=calibration.reference_id,
        calibration_scale=calibration.scale,
        calibration_offset=calibration.offset,
        calibration_valid_samples=calibration.valid_samples,
        provenance=provenance,
    )
