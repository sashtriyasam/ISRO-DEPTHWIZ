"""Validate a produced DSM against a user-supplied reference raster.

PS 26175 asks the platform to let users "validate estimated structural
heights against reference datasets". The reference may be a LiDAR DSM, a
DEM or any single-band height raster in any CRS/resolution:

* georeferenced product + georeferenced reference: the reference is
  reprojected onto the product grid (average when downsampling, bilinear
  when upsampling) and compared in metres;
* product without CRS (relative run): the reference is resampled to the
  product size, assumed to cover the same extent, and only scale-free
  agreement (Pearson / Spearman correlation) is reported — never metres.

Metrics: RMSE, MAE, bias (product - reference), Pearson r, Spearman rho,
coverage, plus the same at a coarse block scale for DEM-like references.
"""

from __future__ import annotations

import math
import warnings
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from depthwizard.errors import InvalidInputError


def _align_reference(product: Path, reference: Path) -> tuple[np.ndarray, np.ndarray, bool]:
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import reproject

    with rasterio.open(product) as p:
        values = p.read(1, masked=True).astype(np.float64).filled(np.nan)
        p_crs, p_transform, p_res = p.crs, p.transform, p.res
    with rasterio.open(reference) as r:
        r_crs = r.crs
        georeferenced = p_crs is not None and r_crs is not None
        target = np.full(values.shape, np.nan, dtype=np.float64)
        if georeferenced:
            downsample = abs(r.res[0]) < abs(p_res[0])
            reproject(
                source=rasterio.band(r, 1),
                destination=target,
                src_nodata=r.nodata,
                dst_transform=p_transform,
                dst_crs=p_crs,
                dst_nodata=np.nan,
                resampling=Resampling.average if downsample else Resampling.bilinear,
            )
        else:
            data = r.read(
                1,
                out_shape=values.shape,
                resampling=Resampling.bilinear,
                masked=True,
            )
            target = data.astype(np.float64).filled(np.nan)
    return values, target, georeferenced


def _rank(a: NDArray[np.float64]) -> NDArray[np.float64]:
    order = a.argsort(kind="stable")
    ranks = np.empty(a.size, dtype=np.float64)
    ranks[order] = np.arange(a.size, dtype=np.float64)
    return ranks


def _corr(a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
    if a.size < 3 or a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def _block(a: NDArray[np.float64], k: int) -> NDArray[np.float64]:
    h, w = (a.shape[0] // k) * k, (a.shape[1] // k) * k
    if h == 0 or w == 0:
        return a
    b = a[:h, :w].reshape(h // k, k, w // k, k)
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN blocks -> NaN
        return np.nanmean(np.nanmean(b, axis=3), axis=1)


def _scores(
    pred: NDArray[np.float64], ref: NDArray[np.float64], metric: bool
) -> dict[str, float | int | None]:
    ok = np.isfinite(pred) & np.isfinite(ref)
    p, r = pred[ok], ref[ok]
    sample = slice(None)
    if p.size > 2_000_000:  # rank correlation on an even subsample
        sample = slice(None, None, p.size // 2_000_000 + 1)
    scores: dict[str, float | int | None] = {
        "n": int(ok.sum()),
        "pearson_r": _corr(p, r),
        "spearman_rho": _corr(_rank(p[sample]), _rank(r[sample])),
    }
    if metric and p.size:
        err = p - r
        scores.update(
            rmse=float(math.sqrt(float(np.mean(err**2)))),
            mae=float(np.mean(np.abs(err))),
            bias=float(np.mean(err)),
        )
    else:
        scores.update(rmse=None, mae=None, bias=None)
    return scores


def validate_dsm(
    product: str | Path, reference: str | Path, coarse_m: float = 30.0
) -> dict[str, object]:
    """Compare a product raster against a reference raster (see module doc)."""
    product, reference = Path(product), Path(reference)
    for path in (product, reference):
        if not path.is_file():
            raise InvalidInputError(f"validation input not found: {path.name}")
    try:
        values, target, georeferenced = _align_reference(product, reference)
    except Exception as exc:
        raise InvalidInputError(f"cannot align reference {reference.name}: {exc}") from exc
    coverage = float(np.isfinite(target).mean()) if target.size else 0.0
    if coverage == 0.0:
        raise InvalidInputError("the reference does not overlap the product")
    result: dict[str, object] = {
        "product": product.name,
        "reference": reference.name,
        "metric": georeferenced,
        "coverage": coverage,
        "native": _scores(values, target, georeferenced),
    }
    if georeferenced:
        import rasterio

        with rasterio.open(product) as p:
            pixel = abs(p.res[0])
            projected = bool(p.crs and p.crs.is_projected)
        if projected and pixel > 0:
            k = max(1, int(round(coarse_m / pixel)))
            if k > 1:
                result["coarse"] = {
                    "block_m": k * pixel,
                    **_scores(_block(values, k), _block(target, k), True),
                }
    else:
        result["note"] = (
            "Product has no CRS (relative run): the reference was resized to the image and "
            "only scale-free correlation is reported."
        )
    return result
