"""
Per-image affine alignment + scale-aware metrics (evaluation only).

`evaluate_sample` returns a dict with two strictly separated sections:
    "raw": prediction distribution statistics (NO error vs target).
    "aligned": affine-fit parameters + MAE/RMSE/correlation vs GAMUS target.

Fitting is deterministic closed-form least squares on masked pixels of a
single image. Degenerate predictions (zero variance) yield a=None, b=target
mean fallback, flagged via `degenerate=True` — never NaN metrics.
"""

from __future__ import annotations

from typing import Any, Optional


def _np():
    try:
        import numpy as np  # type: ignore
    except Exception as e:
        raise RuntimeError(f"numpy is required for evaluation: {e}") from e
    return np


def build_mask(prediction: Any, target: Any) -> Any:
    """Deterministic valid mask: finite pred AND finite target. Keeps negatives."""
    np = _np()
    p = np.asarray(prediction, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    if p.shape != t.shape:
        raise ValueError(f"Prediction shape {p.shape} != target shape {t.shape}")
    return np.isfinite(p) & np.isfinite(t)


def affine_fit(prediction: Any, target: Any, mask: Optional[Any] = None) -> tuple[Optional[float], Optional[float], bool]:
    """Least-squares `target ~= a*pred + b` on masked pixels.

    Returns (a, b, degenerate). If fewer than 2 valid pixels or zero
    prediction variance: (None, None, True) — caller must handle explicitly.
    """
    np = _np()
    p = np.asarray(prediction, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    m = np.asarray(mask, dtype=bool) if mask is not None else build_mask(p, t)
    if p.shape != t.shape or m.shape != p.shape:
        raise ValueError("prediction/target/mask shapes must agree")
    pv, tv = p[m], t[m]
    if pv.size < 2:
        return None, None, True
    if float(pv.var()) == 0.0:
        return None, None, True
    a_mat = np.stack([pv, np.ones_like(pv)], axis=1)
    (a, b), *_ = np.linalg.lstsq(a_mat, tv, rcond=None)
    return float(a), float(b), False


def apply_affine(prediction: Any, a: float, b: float) -> Any:
    np = _np()
    return np.asarray(prediction, dtype=np.float64) * float(a) + float(b)


def mae(aligned: Any, target: Any, mask: Any) -> float:
    np = _np()
    a = np.asarray(aligned, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    m = np.asarray(mask, dtype=bool)
    return float(np.abs(a[m] - t[m]).mean())


def rmse(aligned: Any, target: Any, mask: Any) -> float:
    np = _np()
    a = np.asarray(aligned, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    m = np.asarray(mask, dtype=bool)
    return float(np.sqrt(((a[m] - t[m]) ** 2).mean()))


def pearson(prediction: Any, target: Any, mask: Any) -> Optional[float]:
    """Pearson r on masked pixels; None when either side is constant."""
    np = _np()
    p = np.asarray(prediction, dtype=np.float64)[np.asarray(mask, dtype=bool)]
    t = np.asarray(target, dtype=np.float64)[np.asarray(mask, dtype=bool)]
    if p.size < 2 or float(p.var()) == 0.0 or float(t.var()) == 0.0:
        return None
    c = np.corrcoef(p, t)
    return float(c[0, 1])


def _ranks(x: Any) -> Any:
    np = _np()
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(x.size, dtype=np.float64)
    # Average ranks for ties.
    _, inv, counts = np.unique(x, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks)
    avg = sums / counts
    return avg[inv]


def spearman(prediction: Any, target: Any, mask: Any) -> Optional[float]:
    """Spearman rho via ranked Pearson (numpy-only); None on degenerate input."""
    np = _np()
    m = np.asarray(mask, dtype=bool)
    p = np.asarray(prediction, dtype=np.float64)[m]
    t = np.asarray(target, dtype=np.float64)[m]
    if p.size < 2:
        return None
    return pearson(_ranks(p), _ranks(t), np.ones(p.shape, dtype=bool))


def evaluate_sample(prediction: Any, target: Any, mask: Optional[Any] = None) -> dict[str, Any]:
    """Full per-sample evaluation. Never emits raw-pred-vs-meter error numbers."""
    np = _np()
    p = np.asarray(prediction, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    m = np.asarray(mask, dtype=bool) if mask is not None else build_mask(p, t)
    total = int(m.size)
    valid = int(m.sum())
    raw_finite = p[np.isfinite(p)]
    out: dict[str, Any] = {
        "protocol": "per-image-affine-eval-v1 (evaluation only, not calibration)",
        "n_pixels": total,
        "n_valid": valid,
        "valid_coverage": (valid / total) if total else 0.0,
        "raw": {
            "min": float(raw_finite.min()) if raw_finite.size else None,
            "max": float(raw_finite.max()) if raw_finite.size else None,
            "mean": float(raw_finite.mean()) if raw_finite.size else None,
            "std": float(raw_finite.std()) if raw_finite.size else None,
        },
    }
    a, b, degenerate = affine_fit(p, t, m)
    out["affine"] = {"a": a, "b": b, "degenerate": degenerate, "per_image_only": True}
    if degenerate or a is None or b is None:
        out["aligned"] = {"mae": None, "rmse": None, "note": "degenerate prediction or <2 valid pixels"}
    else:
        aligned = apply_affine(p, a, b)
        out["aligned"] = {"mae": mae(aligned, t, m), "rmse": rmse(aligned, t, m)}
    out["pearson"] = pearson(p, t, m)
    out["spearman"] = spearman(p, t, m)
    return out
