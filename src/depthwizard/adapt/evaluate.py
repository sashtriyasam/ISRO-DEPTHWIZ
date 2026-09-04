"""
Validation analysis for adapted metric predictions (M4, research only).

Reports direct-meter metrics (MAE/RMSE/median/p90/p95/Pearson/Spearman),
per-class breakdowns from GAMUS labels (missing classes -> "not present",
never zero-filled), and height-bin breakdowns. No calibration involved.
"""

from __future__ import annotations

from typing import Any, Optional

HEIGHT_BINS = [(0.0, 1.0, "0-1m"), (1.0, 5.0, "1-5m"), (5.0, 10.0, "5-10m"), (10.0, 20.0, "10-20m"), (20.0, 30.0, "20-30m"), (30.0, float("inf"), "30+m")]


def _require_np() -> Any:
    try:
        import numpy as np  # type: ignore
    except Exception as e:
        raise RuntimeError(f"numpy required: {e}") from e
    return np


def _stats(abs_err: Any) -> dict[str, Any]:
    np = _require_np()
    e = np.asarray(abs_err, dtype=np.float64)
    if e.size == 0:
        return {"n": 0, "mae": None, "rmse": None, "median": None, "p90": None, "p95": None}
    return {
        "n": int(e.size),
        "mae": float(e.mean()),
        "rmse": float(np.sqrt((e ** 2).mean())),
        "median": float(np.median(e)),
        "p90": float(np.percentile(e, 90)),
        "p95": float(np.percentile(e, 95)),
    }


def _corr(p: Any, t: Any) -> dict[str, Optional[float]]:
    np = _require_np()
    p, t = np.asarray(p, dtype=np.float64), np.asarray(t, dtype=np.float64)
    if p.size < 2 or float(p.var()) == 0.0 or float(t.var()) == 0.0:
        return {"pearson": None, "spearman": None}
    pearson = float(np.corrcoef(p, t)[0, 1])
    order = np.argsort(p, kind="mergesort")
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(p.size, dtype=np.float64)
    _, inv, counts = np.unique(p, return_inverse=True, return_counts=True)
    rp = (np.bincount(inv, weights=ranks) / counts)[inv]
    order_t = np.argsort(t, kind="mergesort")
    ranks_t = np.empty_like(order_t, dtype=np.float64)
    ranks_t[order_t] = np.arange(t.size, dtype=np.float64)
    _, inv_t, counts_t = np.unique(t, return_inverse=True, return_counts=True)
    rt = (np.bincount(inv_t, weights=ranks_t) / counts_t)[inv_t]
    spearman = float(np.corrcoef(rp, rt)[0, 1]) if rp.var() and rt.var() else None
    return {"pearson": pearson, "spearman": spearman}


def evaluate_predictions(
    preds: list[Any],
    targets: list[Any],
    labels: Optional[list[Any]] = None,
    class_names: Optional[dict[int, str]] = None,
) -> dict[str, Any]:
    """Aggregate pixel-level analysis over validation samples.

    preds/targets: list of (H,W) float arrays. labels: optional (H,W) int arrays.
    Mask: finite pred AND finite target (negatives kept).
    """
    np = _require_np()
    P = [np.asarray(p, dtype=np.float64).ravel() for p in preds]
    T = [np.asarray(t, dtype=np.float64).ravel() for t in targets]
    pall, tall = np.concatenate(P), np.concatenate(T)
    mask = np.isfinite(pall) & np.isfinite(tall)
    pv, tv = pall[mask], tall[mask]
    abs_err = np.abs(pv - tv)
    out: dict[str, Any] = {
        "n_pixels": int(pall.size),
        "n_valid": int(mask.sum()),
        "valid_coverage": float(mask.mean()) if pall.size else 0.0,
        "error": _stats(abs_err),
        "correlation": _corr(pv, tv),
    }
    # Height bins (by TARGET value; negative targets fall outside bins -> reported).
    out["height_bins"] = {}
    for lo, hi, name in HEIGHT_BINS:
        m = (tv >= lo) & (tv < hi)
        s = _stats(abs_err[m])
        s["fraction"] = float(m.sum() / max(1, tv.size))
        out["height_bins"][name] = s
    neg = tv < 0
    out["negative_target_pixels"] = {"n": int(neg.sum()), **_stats(abs_err[neg])} if neg.any() else {"n": 0}
    # Per-class (label rounded to int; unknown ids reported, never zero-filled).
    out["per_class"] = {}
    if labels is not None:
        lab_all = np.concatenate([np.asarray(lab).ravel() for lab in labels])
        Lv = np.round(lab_all[mask]).astype(int)
        for cid in sorted(set(int(v) for v in np.unique(Lv))):
            m = Lv == cid
            name = (class_names or {}).get(cid, f"class_{cid}")
            out["per_class"][name] = {"id": cid, **_stats(abs_err[m])}
    return out
