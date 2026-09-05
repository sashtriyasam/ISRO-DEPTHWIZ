"""Relative surface rasterization: RELATIVE DepthResult → rDSM grid.

The only sanctioned path from model output to a relative surface.
Rejects anything that already claims metric scale or meaning — a
relative grid is never built from calibrated output.
"""

from __future__ import annotations

import numpy as np

from depthwizard.contracts.artifacts import DepthResult
from depthwizard.contracts.semantics import DepthScale, ElevationSemantics
from depthwizard.errors import InvalidInputError
from depthwizard.rdsm.models import RelativeSurfaceGrid

_RELATIVE_MEANINGS = frozenset(
    {
        ElevationSemantics.RELATIVE_DEPTH,
        ElevationSemantics.RELATIVE_SURFACE_RDSM,
    }
)


def rasterize_relative_surface(depth: DepthResult) -> RelativeSurfaceGrid:
    """Rasterize relative depth values into an rDSM grid (no resampling).

    The source ``DepthResult`` is never mutated. Callers needing metric
    output must use the calibrated ``height``/``dsm`` path instead.
    """
    if not isinstance(depth, DepthResult):
        raise TypeError(
            f"rasterize_relative_surface requires a DepthResult; got {type(depth).__name__}"
        )
    if depth.depth_scale is not DepthScale.RELATIVE:
        raise InvalidInputError(
            "relative surfaces are built from RELATIVE depth; "
            f"this DepthResult claims {depth.depth_scale.value} scale"
        )
    if depth.elevation_semantics not in _RELATIVE_MEANINGS:
        raise InvalidInputError(
            "relative surfaces require a relative depth source; "
            f"got elevation semantics '{depth.elevation_semantics.value}'"
        )
    width = depth.output_resolution.width
    height = depth.output_resolution.height
    array = np.asarray(depth.depth_values, dtype=np.float64).reshape(height, width)
    if depth.valid_mask is not None:
        declared = np.asarray(depth.valid_mask, dtype=bool).reshape(height, width)
        valid = np.ascontiguousarray(declared & np.isfinite(array))
    else:
        valid = np.ascontiguousarray(np.isfinite(array))
    array = np.ascontiguousarray(array.astype(np.float32))
    return RelativeSurfaceGrid(
        array=array,
        valid_mask=valid,
        width=width,
        height=height,
        dtype=str(array.dtype),
        units=None,
        semantics=ElevationSemantics.RELATIVE_SURFACE_RDSM,
        invalid_count=int((~valid).sum()),
        georeferencing=depth.georeferencing,
        spatial=depth.spatial,
        depth_model_name=depth.model_name,
        depth_model_version=depth.model_version,
        depth_checkpoint_id=depth.checkpoint_id,
        source_input_id=depth.provenance.source_input_id,
        source_checksum=depth.provenance.input_checksum,
        provenance=depth.provenance,
    )
