"""Reference-control construction (fail-fast, no fitting, no products).

``build_reference_control`` resolves one surface control against a
relative depth result (plus a terrain grid for AGL) into a fully
auditable ``ReferenceControlPoint``. ``build_calibration_samples``
packs ordered points into S9 ``CalibrationSamples``. Neither fits,
applies, or produces height products — S9/S10 own those steps.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from depthwizard.calibration.models import CalibrationSamples
from depthwizard.contracts.artifacts import DepthResult
from depthwizard.contracts.semantics import (
    DepthScale,
    ElevationSemantics,
    GeoreferencingLevel,
)
from depthwizard.contracts.spatial import AffineTransform, SpatialKind
from depthwizard.controls.models import (
    CoordinateSpace,
    ReferenceControlPoint,
    SurfaceElevationControl,
)
from depthwizard.dem.models import TerrainReferenceGrid
from depthwizard.dem.sample import sample_terrain_at_world
from depthwizard.errors import (
    CalibrationError,
    DemMismatchError,
    GeospatialProcessingError,
    InvalidInputError,
    MissingCRSError,
    MissingElevationReferenceError,
)
from depthwizard.geospatial.crs import crs_equal
from depthwizard.geospatial.transforms import pixel_to_world, world_to_pixel

_METRIC_TARGETS = frozenset(
    {
        ElevationSemantics.HEIGHT_AGL_NDSM,
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    }
)

#: Pixel/world agreement tolerance (relative + absolute), documented.
_CONSISTENCY_REL_TOL = 1e-6
_CONSISTENCY_ABS_TOL = 1e-6


def _resolve_pixel(
    depth: DepthResult, surface: SurfaceElevationControl
) -> tuple[int, int, float | None, float | None, float | None, float | None]:
    """Resolve (row, col) plus world/continuous coordinates if placeable.

    Returns row, col, x, y, pixel_col, pixel_row. World values are None
    when the source frame cannot place the pixel (non-georeferenced).
    """
    width = depth.output_resolution.width
    height = depth.output_resolution.height
    if surface.coordinate_space is CoordinateSpace.PIXEL:
        assert surface.row is not None and surface.col is not None
        row, col = surface.row, surface.col
        if row >= height or col >= width:
            raise InvalidInputError(
                f"control {surface.control_id!r} pixel ({row}, {col}) lies "
                f"outside the {width}x{height} prediction grid"
            )
        world = _pixel_center_world(depth, row, col)
        if world is None:
            return row, col, None, None, None, None
        x, y = world
        if surface.x is not None and surface.y is not None:
            _check_consistency(surface.control_id, x, y, surface.x, surface.y)
        return row, col, x, y, None, None
    assert surface.x is not None and surface.y is not None
    frame = _source_frame(depth, surface.control_id)
    cont_col, cont_row = world_to_pixel(frame, surface.x, surface.y)
    row, col = math.floor(cont_row), math.floor(cont_col)
    if row < 0 or col < 0 or row >= height or col >= width:
        raise InvalidInputError(
            f"control {surface.control_id!r} world ({surface.x}, {surface.y}) "
            f"resolves outside the {width}x{height} prediction grid"
        )
    if surface.row is not None and surface.col is not None:
        if (surface.row, surface.col) != (row, col):
            raise GeospatialProcessingError(
                f"control {surface.control_id!r} pixel/world coordinates contradict: "
                f"world implies ({row}, {col}), given ({surface.row}, {surface.col})"
            )
    return row, col, surface.x, surface.y, cont_col, cont_row


def _source_frame(depth: DepthResult, control_id: str) -> AffineTransform:
    """Return the depth transform for world placement (fail loudly)."""
    if depth.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED:
        raise MissingCRSError(
            f"control {control_id!r} uses world coordinates, but the depth "
            "source is non-georeferenced (no CRS invented)"
        )
    details = depth.spatial.details if depth.spatial.kind is SpatialKind.PRESENT else None
    if details is None or details.transform is None:
        raise GeospatialProcessingError(
            f"control {control_id!r} needs a source affine transform, none available"
        )
    return details.transform


def _pixel_center_world(depth: DepthResult, row: int, col: int) -> tuple[float, float] | None:
    """World center of a pixel, or None when unplaceable (non-georeferenced)."""
    if depth.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED:
        return None
    details = depth.spatial.details if depth.spatial.kind is SpatialKind.PRESENT else None
    if details is None or details.transform is None:
        return None
    return pixel_to_world(details.transform, float(col), float(row))


def _check_consistency(
    control_id: str, expected_x: float, expected_y: float, given_x: float, given_y: float
) -> None:
    """Reject contradictory dual-coordinate controls (documented tolerance)."""
    if not (
        math.isclose(
            expected_x, given_x, rel_tol=_CONSISTENCY_REL_TOL, abs_tol=_CONSISTENCY_ABS_TOL
        )
        and math.isclose(
            expected_y, given_y, rel_tol=_CONSISTENCY_REL_TOL, abs_tol=_CONSISTENCY_ABS_TOL
        )
    ):
        raise GeospatialProcessingError(
            f"control {control_id!r} pixel/world coordinates contradict: "
            f"pixel implies ({expected_x}, {expected_y}), "
            f"given ({given_x}, {given_y})"
        )


def _check_control_crs(depth: DepthResult, surface: SurfaceElevationControl) -> None:
    """Refuse cross-CRS controls (no control reprojection this milestone)."""
    if surface.crs is None:
        return
    details = depth.spatial.details if depth.spatial.kind is SpatialKind.PRESENT else None
    if details is None or details.crs is None:
        raise MissingCRSError(
            f"control {surface.control_id!r} declares CRS {surface.crs!r}, "
            "but the depth source carries none"
        )
    if not crs_equal(surface.crs, details.crs):
        raise GeospatialProcessingError(
            f"control {surface.control_id!r} CRS {surface.crs!r} differs from "
            f"source CRS {details.crs!r}; controls are not reprojected"
        )


def _predicted_value(depth: DepthResult, control_id: str, row: int, col: int) -> float:
    """Extract the exact relative prediction (fail on invalid cells)."""
    width = depth.output_resolution.width
    index = row * width + col
    if depth.valid_mask is not None and not depth.valid_mask[index]:
        raise InvalidInputError(
            f"control {control_id!r} references invalid prediction cell ({row}, {col})"
        )
    value = depth.depth_values[index]
    if not math.isfinite(value):
        raise InvalidInputError(
            f"control {control_id!r} references non-finite prediction at ({row}, {col})"
        )
    return value


def build_reference_control(
    depth: DepthResult,
    surface: SurfaceElevationControl,
    terrain: TerrainReferenceGrid | None,
    target: ElevationSemantics,
) -> ReferenceControlPoint:
    """Build one auditable reference control (no fitting, no products).

    Absolute path: reference = surface elevation (terrain optional
    context only). AGL path: reference = surface minus valid DEM
    terrain at the same location (terrain mandatory).
    """
    if not isinstance(depth, DepthResult):
        raise TypeError(f"depth must be a DepthResult, got {type(depth).__name__}")
    if not isinstance(surface, SurfaceElevationControl):
        raise TypeError(f"surface must be a SurfaceElevationControl, got {type(surface).__name__}")
    if terrain is not None and not isinstance(terrain, TerrainReferenceGrid):
        raise TypeError(
            f"terrain must be a TerrainReferenceGrid or None, got {type(terrain).__name__}"
        )
    if target not in _METRIC_TARGETS:
        raise CalibrationError(
            f"reference controls target metric height meanings only; got '{target.value}'"
        )
    if depth.depth_scale is not DepthScale.RELATIVE:
        claimed = getattr(depth.depth_scale, "value", depth.depth_scale)
        raise CalibrationError(
            "reference controls consume RELATIVE depth; this DepthResult "
            f"already claims {claimed!r} scale"
        )
    _check_control_crs(depth, surface)
    row, col, x, y, pixel_col, pixel_row = _resolve_pixel(depth, surface)
    predicted = _predicted_value(depth, surface.control_id, row, col)

    terrain_elevation: float | None = None
    if target is ElevationSemantics.HEIGHT_AGL_NDSM:
        if terrain is None:
            raise MissingElevationReferenceError(
                f"control {surface.control_id!r} targets AGL but no terrain "
                "reference was supplied (DEM terrain is mandatory, never assumed)"
            )
        if x is None or y is None:
            raise MissingCRSError(
                f"control {surface.control_id!r} cannot be placed in a world "
                "frame for terrain sampling (no source transform)"
            )
        sample = sample_terrain_at_world(terrain, x, y)
        if not sample.valid or sample.elevation is None:
            raise DemMismatchError(
                f"control {surface.control_id!r} has no valid terrain at "
                f"({x}, {y}) (nodata or outside the reference)"
            )
        terrain_elevation = sample.elevation
        reference = surface.surface_elevation_m - terrain_elevation
    else:
        reference = surface.surface_elevation_m
        if terrain is not None and x is not None and y is not None:
            contextual = sample_terrain_at_world(terrain, x, y)
            if contextual.valid:
                terrain_elevation = contextual.elevation
    if not math.isfinite(reference):
        raise CalibrationError(
            f"control {surface.control_id!r} yields a non-finite reference value"
        )
    return ReferenceControlPoint(
        control_id=surface.control_id,
        target_semantics=target,
        row=row,
        col=col,
        x=x,
        y=y,
        pixel_col=pixel_col,
        pixel_row=pixel_row,
        predicted_value=predicted,
        surface_elevation_m=surface.surface_elevation_m,
        terrain_elevation_m=terrain_elevation,
        reference_value=reference,
        surface_source_id=surface.source_id,
        surface_source_checksum=surface.source_checksum,
        terrain_source_id=terrain.source_dem_id if terrain is not None else None,
        terrain_source_checksum=terrain.source_checksum if terrain is not None else None,
        depth_model=depth.model_name,
        depth_checksum=depth.provenance.input_checksum,
        depth_input_id=depth.provenance.source_input_id,
    )


def build_calibration_samples(
    points: Sequence[ReferenceControlPoint], *, reference_id: str
) -> CalibrationSamples:
    """Pack ordered control points into S9 samples (no fitting).

    Caller order preserved; duplicates, emptiness and mixed targets
    fail fast. Minimum-count enforcement stays in S9 fitting.
    """
    ordered = list(points)
    if not ordered:
        raise InvalidInputError("at least one reference control is required")
    if not reference_id:
        raise InvalidInputError("a reference identifier is required")
    seen: set[str] = set()
    for point in ordered:
        if not isinstance(point, ReferenceControlPoint):
            raise TypeError(
                "build_calibration_samples requires ReferenceControlPoint items, "
                f"got {type(point).__name__}"
            )
        if point.control_id in seen:
            raise InvalidInputError(
                f"duplicate control identifier: {point.control_id!r} "
                "(duplicates are rejected, never averaged)"
            )
        seen.add(point.control_id)
    targets = {point.target_semantics for point in ordered}
    if len(targets) != 1:
        raise InvalidInputError(
            "all controls in one sample set must share their target semantics, "
            f"got {[meaning.value for meaning in targets]}"
        )
    target = ordered[0].target_semantics
    first = ordered[0]
    return CalibrationSamples(
        predicted_values=tuple(point.predicted_value for point in ordered),
        reference_values=tuple(point.reference_value for point in ordered),
        reference_id=reference_id,
        reference_units="meters",
        target_semantics=target,
        source_input_id=first.depth_input_id,
        source_checksum=first.depth_checksum,
    )
