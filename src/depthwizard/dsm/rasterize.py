"""1:1 rasterization of scientific height products (representation only).

Row-major product values map to ``(height, width)`` with no resampling,
reprojection, interpolation, resizing or rescaling. Finite values stay
valid (including 0.0); non-finite values become NaN-marked nodata with
an explicit invalid count. All-invalid input fails explicitly.
"""

from __future__ import annotations

import numpy as np

from depthwizard.dsm.grid import (
    BAND_COUNT,
    NODATA,
    DSMGrid,
    RasterizeOptions,
    ResamplingPolicy,
)
from depthwizard.errors import InvalidInputError
from depthwizard.height.product import ScientificHeightProduct


def rasterize_height_product(
    product: ScientificHeightProduct,
    options: RasterizeOptions | None = None,
) -> DSMGrid:
    """Convert a height product to an owned 2D DSM grid (no file I/O).

    The source product is never mutated; all arrays are freshly
    allocated. Meaning, units, spatial context and provenance pass
    through unchanged — this is representation, not reinterpretation.
    """
    if not isinstance(product, ScientificHeightProduct):
        raise TypeError(
            "rasterize_height_product requires a ScientificHeightProduct; "
            f"got {type(product).__name__}"
        )
    opts = options if options is not None else RasterizeOptions()
    if not isinstance(opts, RasterizeOptions):
        raise TypeError(
            f"rasterize_height_product options must be RasterizeOptions; got {type(opts).__name__}"
        )
    width, height = product.width, product.height
    expected = width * height
    # np.asarray on a tuple always allocates; reshape is C-order
    # (row-major), matching DepthResult/ScientificHeightProduct layout.
    base = np.asarray(product.values, dtype=np.float64).reshape((height, width))
    if base.size != expected:  # defensive: model already guarantees this
        raise InvalidInputError(f"raster value count {base.size} != dimensions {width}x{height}")
    # Overflow to inf on downcast is an explicit policy input: the
    # finiteness mask below is the handling, so the runtime warning
    # would add no information.
    with np.errstate(over="ignore"):
        working = base.astype(opts.dtype, copy=True)
    valid = np.isfinite(working)
    invalid_count = int((~valid).sum())
    if invalid_count == expected:
        raise InvalidInputError(
            f"rasterization refused: all {expected} pixels are non-finite "
            f"({width}x{height}); no valid DSM values exist"
        )
    array = working.copy()
    array[~valid] = NODATA
    return DSMGrid(
        array=array,
        valid_mask=np.ascontiguousarray(valid),
        width=width,
        height=height,
        dtype=str(working.dtype),
        units=product.units,
        semantics=product.semantics,
        nodata=NODATA,
        invalid_count=invalid_count,
        resampling=opts.resampling,
        georeferencing=product.georeferencing,
        spatial=product.spatial,
        depth_model_name=product.depth_model_name,
        depth_model_version=product.depth_model_version,
        depth_checkpoint_id=product.depth_checkpoint_id,
        source_input_id=product.source_input_id,
        source_checksum=product.source_checksum,
        calibration_method=product.calibration_method,
        calibration_reference=product.calibration_reference,
        calibration_scale=product.calibration_scale,
        calibration_offset=product.calibration_offset,
        calibration_valid_samples=product.calibration_valid_samples,
        provenance=product.provenance,
    )


__all__ = ["BAND_COUNT", "NODATA", "ResamplingPolicy", "rasterize_height_product"]
