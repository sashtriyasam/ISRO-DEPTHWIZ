"""DEM-anchored fusion: absolute heights from a low-resolution DEM plus model detail.

Monocular depth on nadir imagery sees structures (buildings, canopy) but
not terrain: a hillside and a plain look alike. An affine fit of relative
depth to a DEM therefore fails exactly where terrain varies. Fusion keeps
each source for what it measures:

    DSM = DEM_up + s * (rel - lowpass_k(rel))

* ``DEM_up``      — reference DEM bilinearly resampled to the image grid
                    (absolute metres, terrain and coarse structure);
* ``lowpass_k``   — mean over the DEM pixel footprint (``k`` image pixels),
                    so the added detail is zero-mean within every DEM cell
                    and the product agrees with the DEM at DEM resolution;
* ``s``           — metres per relative-depth unit, fitted robustly at the
                    structure scale: DEM variation between one and three
                    DEM cells against the same band of the relative depth.

When that structure-scale relation is absent (R² below a floor or a
non-positive slope) ``s = 0`` and the DSM is the resampled DEM, with a
warning — no detail is invented. Expressed as a calibration with a
per-pixel offset field: ``DSM_i = s * rel_i + offset_i``.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from depthwizard.calibration.calibrator import HuberScaleOffsetCalibrator
from depthwizard.calibration.models import (
    CalibrationMethod,
    CalibrationResult,
    CalibrationSamples,
)
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.errors import CalibrationError
from depthwizard.version import __version__

#: Minimum structure-scale R² before model detail is added.
MIN_DETAIL_R_SQUARED = 0.05

#: Samples used for the structure-scale regression (evenly spaced).
MAX_FIT_SAMPLES = 200_000


def box_mean(
    values: NDArray[np.float64], valid: NDArray[np.bool_], size: int
) -> NDArray[np.float64]:
    """Mean over a ``size x size`` window of valid pixels (integral images)."""
    if size <= 1:
        return np.where(valid, values, np.nan)
    half = size // 2
    data = np.where(valid, values, 0.0)
    weight = valid.astype(np.float64)
    padded_d = np.pad(data, half + 1, mode="constant")
    padded_w = np.pad(weight, half + 1, mode="constant")
    sum_d = padded_d.cumsum(0).cumsum(1)
    sum_w = padded_w.cumsum(0).cumsum(1)
    h, w = values.shape

    def window(total: NDArray[np.float64]) -> NDArray[np.float64]:
        r0, c0 = 0, 0
        r1, c1 = 2 * half + 1, 2 * half + 1
        return (
            total[r1 : r1 + h, c1 : c1 + w]
            - total[r0 : r0 + h, c1 : c1 + w]
            - total[r1 : r1 + h, c0 : c0 + w]
            + total[r0 : r0 + h, c0 : c0 + w]
        )

    counts = window(sum_w)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = window(sum_d) / counts
    return np.where(counts > 0, mean, np.nan)


def dem_pixels_in_image(dem_resolution: float, image_resolution: float) -> int:
    """DEM pixel footprint in image pixels (odd, at least 1)."""
    if not (dem_resolution > 0 and image_resolution > 0):
        raise CalibrationError("DEM and image resolutions must be positive")
    k = max(1, int(round(dem_resolution / image_resolution)))
    return k if k % 2 == 1 else k + 1


def dem_anchored_calibration(
    relative: NDArray[np.float64],
    relative_valid: NDArray[np.bool_],
    dem: NDArray[np.float64],
    dem_valid: NDArray[np.bool_],
    k: int,
    *,
    reference_id: str,
    target: ElevationSemantics,
    source_checksum: str | None,
) -> tuple[CalibrationResult, list[str]]:
    """Fit the fusion and return it as a calibration with an offset field."""
    if target is not ElevationSemantics.ABSOLUTE_ELEVATION_DSM:
        raise CalibrationError("DEM-anchored fusion produces absolute elevation (DSM) only")
    if relative.shape != dem.shape:
        raise CalibrationError("relative depth and DEM grids must match")
    usable = relative_valid & dem_valid & np.isfinite(relative) & np.isfinite(dem)
    if int(usable.sum()) < 3:
        raise CalibrationError("DEM does not overlap enough valid image pixels")
    warnings: list[str] = []

    rel = np.where(usable, relative, np.nan).astype(np.float64)
    ref = np.where(usable, dem, np.nan).astype(np.float64)
    rel_k = box_mean(rel, usable, k)
    detail = rel - rel_k

    # Structure-scale band (1..3 DEM cells) of both signals.
    rel_band = rel_k - box_mean(rel, usable, 3 * k)
    ref_band = box_mean(ref, usable, k) - box_mean(ref, usable, 3 * k)
    fit_mask = usable & np.isfinite(rel_band) & np.isfinite(ref_band)
    x = rel_band[fit_mask]
    y = ref_band[fit_mask]
    scale = 0.0
    r_squared = 0.0
    valid_samples = int(x.size)
    if x.size > MAX_FIT_SAMPLES:
        picks = np.linspace(0, x.size - 1, MAX_FIT_SAMPLES).round().astype(np.int64)
        x, y = x[picks], y[picks]
    if x.size >= 3 and float(np.var(x)) > 0.0:
        fit = HuberScaleOffsetCalibrator().calibrate(
            CalibrationSamples(
                predicted_values=tuple(float(v) for v in x),
                reference_values=tuple(float(v) for v in y),
                reference_id=reference_id,
                reference_units="meters",
                target_semantics=target,
            )
        )
        r_squared = fit.r_squared
        if fit.scale > 0.0 and fit.r_squared >= MIN_DETAIL_R_SQUARED:
            scale = fit.scale
    if scale == 0.0:
        warnings.append(
            "DEM-anchored DSM: the depth model's structure did not match the reference "
            f"DEM at its own scale (R² {r_squared:.2f}); the DSM follows the DEM without "
            "added model detail."
        )

    offset = np.where(usable, ref - scale * rel_k, np.nan)
    # Pixels without DEM support keep the nearest-scale DEM mean when available.
    fallback = box_mean(ref, usable, 3 * k)
    offset = np.where(np.isfinite(offset), offset, fallback - scale * np.nan_to_num(rel_k))
    offset = np.where(np.isfinite(offset), offset, float(np.nanmean(ref)))
    added = scale * np.nan_to_num(detail)[usable]
    residual = float(np.sqrt(np.mean(added**2))) if added.size else 0.0
    result = CalibrationResult(
        method=CalibrationMethod.DEM_ANCHORED,
        scale=scale,
        offset=float(np.nanmean(offset)),
        reference_id=reference_id,
        reference_units="meters",
        target_semantics=target,
        total_samples=int(relative.size),
        valid_samples=valid_samples,
        rmse=residual if math.isfinite(residual) else 0.0,
        mae=float(np.mean(np.abs(added))) if added.size else 0.0,
        max_abs_residual=float(np.max(np.abs(added))) if added.size else 0.0,
        r_squared=r_squared,
        engine_version=__version__,
        source_checksum=source_checksum,
        offset_field=tuple(float(v) for v in offset.ravel()),
    )
    return result, warnings
