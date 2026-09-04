"""Artifact-to-transport builders (conversion only, never science).

Each builder maps one validated scientific artifact to its wire form:
no recalibration, no rerasterization, no remeshing, no reprojection,
no resampling, no unit changes, no height exaggeration. NumPy values
become plain Python scalars; NaN leaves the wire entirely (DSM
invalid pixels become null; mesh coordinates must be finite or the
payload is refused).
"""

from __future__ import annotations

import math
from typing import Any

from depthwizard.calibration.models import CalibrationResult
from depthwizard.contracts.artifacts import DepthResult
from depthwizard.dsm.grid import DSMGrid
from depthwizard.errors import InvalidInputError
from depthwizard.integration.transport import (
    TransportBundle,
    TransportCalibrationResult,
    TransportDepthResult,
    TransportDsm,
    TransportFailure,
    TransportMesh,
    TransportProvenance,
    TransportResolution,
    TransportSpatialContext,
    TransportTerrainProduct,
    _finite_or_reject,
    _provenance,
    _spatial,
)
from depthwizard.mesh.models import TerrainMesh
from depthwizard.pipeline.models import PipelineResult


def _float_list(values: Any) -> list[float]:
    """Plain float list from any finite sequence (rejects non-finite)."""
    items = [float(value) for value in values]
    return _finite_or_reject(items, "values")


def _opt_float_list(values: Any | None) -> list[float] | None:
    """Optional float list (None passes through)."""
    if values is None:
        return None
    return _float_list(values)


def _bool_list(values: Any | None) -> list[bool] | None:
    """Optional bool list (None passes through)."""
    if values is None:
        return None
    return [bool(value) for value in values]


def _int_list(values: Any) -> list[int]:
    """Plain int list (indices and source mapping stay exact)."""
    return [int(value) for value in values]


def depth_to_transport(depth: DepthResult) -> TransportDepthResult:
    """Map a depth result (relative stays relative: units None)."""
    if not isinstance(depth, DepthResult):
        raise TypeError(f"expected DepthResult, got {type(depth).__name__}")
    return TransportDepthResult(
        model_name=depth.model_name,
        model_version=depth.model_version,
        checkpoint_id=depth.checkpoint_id,
        input_resolution=TransportResolution(
            width=depth.input_resolution.width, height=depth.input_resolution.height
        ),
        output_resolution=TransportResolution(
            width=depth.output_resolution.width, height=depth.output_resolution.height
        ),
        depth_scale=depth.depth_scale.value,
        elevation_semantics=depth.elevation_semantics.value,
        georeferencing=depth.georeferencing.value,
        depth_values=_float_list(depth.depth_values),
        confidence_values=_opt_float_list(depth.confidence_values),
        valid_mask=_bool_list(depth.valid_mask),
        preprocessing=dict(depth.preprocessing),
        units=depth.units,
        spatial=_spatial(depth.spatial),
        provenance=_provenance(depth.provenance),
    )


def calibration_to_transport(calibration: CalibrationResult) -> TransportCalibrationResult:
    """Map a fitted calibration (parameters verbatim, never refit)."""
    if not isinstance(calibration, CalibrationResult):
        raise TypeError(f"expected CalibrationResult, got {type(calibration).__name__}")
    for name in ("scale", "offset", "rmse", "mae", "max_abs_residual", "r_squared"):
        value = getattr(calibration, name)
        if not math.isfinite(value):
            raise InvalidInputError(
                f"calibration {name} must be finite for transport, got {value!r}"
            )
    return TransportCalibrationResult(
        method=calibration.method.value,
        scale=float(calibration.scale),
        offset=float(calibration.offset),
        reference_id=calibration.reference_id,
        reference_checksum=calibration.reference_checksum,
        reference_units=calibration.reference_units,
        target_semantics=calibration.target_semantics.value,
        total_samples=calibration.total_samples,
        valid_samples=calibration.valid_samples,
        rmse=float(calibration.rmse),
        mae=float(calibration.mae),
        max_abs_residual=float(calibration.max_abs_residual),
        r_squared=float(calibration.r_squared),
        engine_version=calibration.engine_version,
        source_input_id=calibration.source_input_id,
        source_checksum=calibration.source_checksum,
    )


def dsm_to_transport(grid: DSMGrid) -> TransportDsm:
    """Map a DSM grid (invalid pixels become null, valid 0.0 preserved)."""
    if not isinstance(grid, DSMGrid):
        raise TypeError(f"expected DSMGrid, got {type(grid).__name__}")
    flat = grid.array.ravel()
    mask = grid.valid_mask.ravel()
    pairs = zip(flat.tolist(), mask.tolist(), strict=True)
    values: list[float | None] = [float(value) if valid else None for value, valid in pairs]
    for index, (value, valid) in enumerate(zip(values, mask.tolist(), strict=True)):
        if valid and value is not None and not math.isfinite(value):
            raise InvalidInputError(f"dsm value [{index}] marked valid but is not finite")
    return TransportDsm(
        width=grid.width,
        height=grid.height,
        dtype=grid.dtype,
        units=grid.units,
        semantics=grid.semantics.value,
        values=values,
        valid_mask=[bool(value) for value in mask.tolist()],
        invalid_count=grid.invalid_count,
        nodata=None,  # NaN has no JSON form; validity lives in values/mask
        georeferencing=grid.georeferencing.value,
        spatial=_spatial(grid.spatial),
    )


def mesh_to_transport(mesh: TerrainMesh) -> TransportMesh:
    """Map a terrain mesh (all coordinates must be finite)."""
    if not isinstance(mesh, TerrainMesh):
        raise TypeError(f"expected TerrainMesh, got {type(mesh).__name__}")
    return TransportMesh(
        vertices=_float_list(mesh.vertices.ravel().tolist()),
        indices=_int_list(mesh.indices.tolist()),
        normals=_float_list(mesh.normals.ravel().tolist()),
        uvs=_float_list(mesh.uvs.ravel().tolist()),
        vertex_source_indices=_int_list(mesh.vertex_source_indices.tolist()),
        vertex_count=mesh.vertex_count,
        triangle_count=mesh.triangle_count,
        valid_source_pixels=mesh.valid_source_pixels,
        invalid_source_pixels=mesh.invalid_source_pixels,
        skipped_cells=mesh.skipped_cells,
        coverage=float(mesh.coverage),
        frame=mesh.frame.value,
        origin_x=mesh.origin_x,
        origin_y=mesh.origin_y,
        width=mesh.width,
        height=mesh.height,
        units=mesh.units,
        semantics=mesh.semantics.value,
        georeferencing=mesh.georeferencing.value,
        spatial=_spatial(mesh.spatial),
        depth_model_name=mesh.depth_model_name,
        depth_model_version=mesh.depth_model_version,
        depth_checkpoint_id=mesh.depth_checkpoint_id,
        source_input_id=mesh.source_input_id,
        source_checksum=mesh.source_checksum,
        calibration_method=mesh.calibration_method,
        calibration_reference=mesh.calibration_reference,
        calibration_scale=float(mesh.calibration_scale),
        calibration_offset=float(mesh.calibration_offset),
        calibration_valid_samples=mesh.calibration_valid_samples,
        provenance=_provenance(mesh.provenance),
    )


def terrain_product(depth: DepthResult, dsm: DSMGrid, mesh: TerrainMesh) -> TransportTerrainProduct:
    """Assemble the kind-tagged terrain bundle the desktop validates."""
    return TransportTerrainProduct(
        kind="terrain",
        depth_result=depth_to_transport(depth),
        dsm=dsm_to_transport(dsm),
        mesh=mesh_to_transport(mesh),
    )


def bundle_from_pipeline(result: PipelineResult) -> dict[str, Any]:
    """Map a pipeline result to a client-facing bundle (lightweight).

    Returns plain JSON-safe data (not a model): status, state history,
    optional failure, optional serialized artifacts, export path and
    the available-artifact kind list. Large arrays never appear except
    inside the explicitly requested dsm/mesh transport sections.
    """
    bundle = TransportBundle(
        status=result.state.value,
        states=[state.value for state in result.states],
        failure=TransportFailure(
            code=result.failure.error_category,
            message=result.failure.message,
            stage=result.failure.stage.value,
        )
        if result.failure
        else None,
        depth=depth_to_transport(result.depth) if result.depth else None,
        calibration=calibration_to_transport(result.calibration) if result.calibration else None,
        dsm=dsm_to_transport(result.dsm) if result.dsm else None,
        mesh=mesh_to_transport(result.mesh) if result.mesh else None,
        geotiff_path=result.export.path if result.export else None,
        artifacts_available=[
            kind
            for kind, present in (
                ("depth", result.depth is not None),
                ("calibration", result.calibration is not None),
                ("height", result.product is not None),
                ("dsm", result.dsm is not None),
                ("mesh", result.mesh is not None),
                ("geotiff", result.export is not None),
            )
            if present
        ],
    )
    return bundle.model_dump(mode="json")


__all__ = [
    "TransportProvenance",
    "TransportResolution",
    "TransportSpatialContext",
    "bundle_from_pipeline",
    "calibration_to_transport",
    "depth_to_transport",
    "dsm_to_transport",
    "mesh_to_transport",
    "terrain_product",
]
