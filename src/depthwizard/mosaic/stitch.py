"""Stitching multiple georeferenced DSM grids into a city-scale mosaic."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from depthwizard.contracts.artifacts import METRIC_UNIT
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import GeoreferencingLevel
from depthwizard.contracts.spatial import (
    AffineTransform,
    Bounds,
    SpatialContext,
    SpatialDetails,
    SpatialKind,
)
from depthwizard.dsm.grid import NODATA, DSMGrid, ResamplingPolicy
from depthwizard.errors import GeospatialProcessingError, InvalidInputError, MissingCRSError
from depthwizard.geospatial.crs import crs_equal, require_crs
from depthwizard.mosaic.models import MosaicResult, MosaicTileInfo
from depthwizard.version import __version__


def stitch_dsm_grids(grids: Sequence[DSMGrid]) -> MosaicResult:
    """Stitch multiple georeferenced DSM grids into a continuous mosaic.

    Requirements (strictly enforced, no silent approximations):
    1. Input sequence must have at least one grid.
    2. All grids must be georeferenced (Path B). Non-georeferenced grids
       are rejected — coordinates and CRS are never invented.
    3. All grids must share the exact same CRS (no implicit reprojection).
    4. All grids must have compatible pixel sizes (GSDs match within 1%).
    5. All grids must share identical product semantics and units.

    Overlapping regions are averaged across valid samples, maintaining
    nodata where no grid has valid data.
    """
    if not grids:
        raise InvalidInputError("stitch_dsm_grids requires at least one DSMGrid")

    for i, g in enumerate(grids):
        if not isinstance(g, DSMGrid):
            raise TypeError(f"item {i} must be a DSMGrid, got {type(g).__name__}")
        if g.units != METRIC_UNIT:
            raise InvalidInputError(
                f"grid {i} units must be metric ('{METRIC_UNIT}'), got '{g.units}'"
            )
        if g.spatial.kind is not SpatialKind.PRESENT or g.spatial.details is None:
            raise MissingCRSError(
                f"grid {i} is not georeferenced; mosaic requires explicit spatial transform and CRS"
            )

    first = grids[0]
    base_crs = require_crs(first.spatial, "mosaic stitching")
    base_semantics = first.semantics

    assert first.spatial.details is not None
    assert first.spatial.details.transform is not None
    base_t = first.spatial.details.transform
    res_x = abs(float(base_t.a))
    res_y = abs(float(base_t.e))

    # Verify compatibility across all grids
    for i, g in enumerate(grids[1:], start=1):
        if g.semantics != base_semantics:
            raise InvalidInputError(
                f"grid {i} semantics '{g.semantics.value}' disagrees "
                f"with base '{base_semantics.value}'"
            )
        crs_i = require_crs(g.spatial, "mosaic stitching")
        if not crs_equal(base_crs, crs_i):
            raise GeospatialProcessingError(
                f"grid {i} CRS '{crs_i}' differs from base CRS '{base_crs}'; "
                "mosaic requires matching CRS"
            )
        assert g.spatial.details is not None
        assert g.spatial.details.transform is not None
        t_i = g.spatial.details.transform
        gx = abs(float(t_i.a))
        gy = abs(float(t_i.e))
        if not (math.isclose(res_x, gx, rel_tol=0.01) and math.isclose(res_y, gy, rel_tol=0.01)):
            raise GeospatialProcessingError(
                f"grid {i} pixel resolution ({gx:.4f}, {gy:.4f}) disagrees "
                f"with base ({res_x:.4f}, {res_y:.4f})"
            )

    # Compute bounding boxes in world space for all grids
    # Standard north-up GeoTIFF: x = c + col * a, y = f + row * e (e is negative)
    world_bounds: list[tuple[float, float, float, float]] = []
    tile_infos: list[MosaicTileInfo] = []

    for g in grids:
        assert g.spatial.details is not None
        assert g.spatial.details.transform is not None
        t = g.spatial.details.transform
        w, h = g.width, g.height

        x0 = float(t.c)
        x1 = x0 + w * float(t.a)
        y0 = float(t.f)
        y1 = y0 + h * float(t.e)

        min_x, max_x = min(x0, x1), max(x0, x1)
        min_y, max_y = min(y0, y1), max(y0, y1)
        world_bounds.append((min_x, max_x, min_y, max_y))

        tile_infos.append(
            MosaicTileInfo(
                source_input_id=g.source_input_id,
                source_checksum=g.source_checksum,
                width=g.width,
                height=g.height,
                valid_count=int(g.valid_mask.sum()),
            )
        )

    # Union bounding box
    union_min_x = min(b[0] for b in world_bounds)
    union_max_x = max(b[1] for b in world_bounds)
    union_min_y = min(b[2] for b in world_bounds)
    union_max_y = max(b[3] for b in world_bounds)

    mosaic_w = int(round((union_max_x - union_min_x) / res_x))
    mosaic_h = int(round((union_max_y - union_min_y) / res_y))

    if mosaic_w <= 0 or mosaic_h <= 0:
        raise GeospatialProcessingError("computed mosaic dimensions are non-positive")

    # Target affine transform (north-up: e < 0)
    mosaic_transform = AffineTransform(
        a=res_x,
        b=0.0,
        c=union_min_x,
        d=0.0,
        e=-res_y,
        f=union_max_y,
    )

    # Accumulator buffers
    accum_sum = np.zeros((mosaic_h, mosaic_w), dtype=np.float64)
    accum_count = np.zeros((mosaic_h, mosaic_w), dtype=np.int32)

    for g in grids:
        assert g.spatial.details is not None
        assert g.spatial.details.transform is not None
        t = g.spatial.details.transform
        g_x0 = float(t.c)
        g_y0 = float(t.f)

        # Offset in mosaic pixels
        col_offset = int(round((g_x0 - union_min_x) / res_x))
        row_offset = int(round((union_max_y - g_y0) / res_y))

        for r in range(g.height):
            mr = row_offset + r
            if not (0 <= mr < mosaic_h):
                continue
            for c in range(g.width):
                mc = col_offset + c
                if not (0 <= mc < mosaic_w):
                    continue
                if g.valid_mask[r, c]:
                    val = float(g.array[r, c])
                    if math.isfinite(val):
                        accum_sum[mr, mc] += val
                        accum_count[mr, mc] += 1

    mosaic_valid = accum_count > 0
    mosaic_array = np.full((mosaic_h, mosaic_w), NODATA, dtype=np.float32)
    mosaic_array[mosaic_valid] = (
        accum_sum[mosaic_valid] / accum_count[mosaic_valid]
    ).astype(np.float32)

    overlap_count = int((accum_count > 1).sum())
    invalid_count = int((~mosaic_valid).sum())

    mosaic_bounds = Bounds(
        min_x=union_min_x,
        min_y=union_min_y,
        max_x=union_max_x,
        max_y=union_max_y,
    )

    spatial_ctx = SpatialContext(
        kind=SpatialKind.PRESENT,
        details=SpatialDetails(
            crs=base_crs,
            transform=mosaic_transform,
            bounds=mosaic_bounds,
        ),
    )

    # Provenance
    input_ids = [t.source_input_id for t in tile_infos if t.source_input_id]
    combined_input_id = ";".join(input_ids) if input_ids else "mosaic"
    provenance = ProductProvenance(
        source_input_id=combined_input_id,
        input_checksum=None,
        model_name="multi-tile-mosaic",
        model_version=None,
        checkpoint_id=None,
        software_version=__version__,
        generated_at=None,
        units=METRIC_UNIT,
        semantic_meaning=f"stitched {len(grids)}-tile mosaic ({base_semantics.value})",
    )

    grid = DSMGrid(
        array=mosaic_array,
        valid_mask=mosaic_valid,
        width=mosaic_w,
        height=mosaic_h,
        dtype="float32",
        units=METRIC_UNIT,
        semantics=base_semantics,
        nodata=NODATA,
        invalid_count=invalid_count,
        resampling=ResamplingPolicy.NO_RESAMPLING,
        georeferencing=GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE,
        spatial=spatial_ctx,
        depth_model_name="mosaic-composite",
        depth_model_version=None,
        depth_checkpoint_id=None,
        source_input_id=combined_input_id,
        source_checksum=None,
        calibration_method="composite",
        calibration_reference="composite",
        calibration_scale=1.0,
        calibration_offset=0.0,
        calibration_valid_samples=int(mosaic_valid.sum()),
        provenance=provenance,
    )

    return MosaicResult(
        mosaic_grid=grid,
        tiles=tuple(tile_infos),
        tile_count=len(grids),
        overlap_pixel_count=overlap_count,
    )
