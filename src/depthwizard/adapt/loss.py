"""
Masked L1 regression loss with optional target normalization (M7).

Formulation: mean |pred - target| over pixels where BOTH are finite.
Negative targets preserved (no clipping, no -5.0 special-casing).
Returns (loss_tensor, n_valid). Raises on zero valid pixels instead of
returning a fake zero loss.

TargetScale supports:
    mode="raw": identity forward/inverse (M4/M5 raw meters).
    mode="zscore": z = (y - mu) / sigma computed from TRAIN pixels only.

``masked_height_weighted_l1`` (M12) keeps the z-space comparison but weights
pixels by the meter-scale target (2x below 5 m, 1x at/above).

``pearson_distance`` (M17) is a scale/shift-decoupled structural objective:
``1 - Pearson(pred, target)`` over valid pixels. Constant or zero-variance
inputs yield the neutral worst score 1.0 (never a misleading perfect score).
"""

from __future__ import annotations

from typing import Any

import torch


class TargetScale:
    """Target representation contract.

    mode="raw": identity forward/inverse (no statistics, no leakage surface).
    mode="zscore": z = (y - mu) / sigma with stats from TRAIN data only.
    Any future mode must compute stats from TRAIN data only and persist them.
    """

    def __init__(self, mode: str = "raw", mu: float = 0.0, sigma: float = 1.0) -> None:
        if mode not in ("raw", "zscore"):
            raise ValueError(f"Unsupported target mode {mode!r}: supported 'raw', 'zscore'")
        self.mode = mode
        self.mu = float(mu)
        self.sigma = float(sigma)
        if self.mode == "zscore" and self.sigma <= 0.0:
            raise ValueError("zscore mode requires sigma > 0")

    def forward(self, target: Any) -> Any:
        if self.mode == "raw":
            return target
        # zscore: z = (y - mu) / sigma
        return (target - self.mu) / self.sigma

    def inverse(self, pred: Any) -> Any:
        if self.mode == "raw":
            return pred
        # inverse zscore: y = z * sigma + mu
        return pred * self.sigma + self.mu

    def config(self) -> dict:
        if self.mode == "raw":
            return {"mode": "raw", "normalization": "none (raw meters)"}
        return {
            "mode": "zscore",
            "mu": self.mu,
            "sigma": self.sigma,
            "normalization": "zscore (train pixels only)",
        }


def _require_torch() -> Any:
    try:
        import torch  # type: ignore
    except Exception as e:
        raise RuntimeError(f"torch is required for M4/M7 adaptation (pip install -e .[dav2]): {e}") from e
    return torch


def masked_l1(pred: Any, target: Any) -> tuple[Any, int]:
    torch = _require_torch()
    if pred.shape != target.shape:
        raise ValueError(f"pred shape {tuple(pred.shape)} != target shape {tuple(target.shape)}")
    mask = torch.isfinite(pred) & torch.isfinite(target)
    n_valid = int(mask.sum().item())
    if n_valid == 0:
        raise ValueError("masked_l1: zero valid pixels (all non-finite)")
    loss = torch.abs(pred[mask] - target[mask]).mean()
    if not torch.isfinite(loss).item():
        raise ValueError("masked_l1: non-finite loss")
    return loss, n_valid


def masked_height_weighted_l1(
    pred_z: Any,
    target_z: Any,
    target_m: Any,
    threshold: float = 5.0,
    low_weight: float = 2.0,
) -> tuple[Any, int]:
    """Low-height-weighted masked L1 (M12).

    Compares z-score prediction/target exactly like :func:`masked_l1`, but
    weights each valid pixel by the ORIGINAL METER-SCALE target
    (``target_m``), assigned BEFORE any z-score conversion:

        w = low_weight  if target_m < threshold
        w = 1.0         otherwise (including negative targets, which are < threshold)

        loss = sum(w * |pred_z - target_z|) / sum(w)

    Finite-pred AND finite-target masking is identical to :func:`masked_l1`
    (finiteness is invariant under the z-score affine map, so masking on
    either scale selects the same pixels). Negative targets are preserved
    and fall in the weighted group. No class labels, no validation data.
    """
    torch = _require_torch()
    if pred_z.shape != target_z.shape or pred_z.shape != target_m.shape:
        raise ValueError(
            f"shape mismatch pred_z {tuple(pred_z.shape)} vs "
            f"target_z {tuple(target_z.shape)} vs target_m {tuple(target_m.shape)}"
        )
    if not (low_weight > 0.0):
        raise ValueError(f"low_weight must be positive, got {low_weight!r}")
    mask = torch.isfinite(pred_z) & torch.isfinite(target_z) & torch.isfinite(target_m)
    n_valid = int(mask.sum().item())
    if n_valid == 0:
        raise ValueError("masked_height_weighted_l1: zero valid pixels (all non-finite)")
    w = torch.where(target_m[mask] < float(threshold), float(low_weight), 1.0)
    loss = (w * torch.abs(pred_z[mask] - target_z[mask])).sum() / w.sum()
    if not torch.isfinite(loss).item():
        raise ValueError("masked_height_weighted_l1: non-finite loss")
    return loss, n_valid


def pearson_distance(pred: Any, target: Any) -> tuple[Any, int]:
    """Scale/shift-decoupled structural loss (M17): ``1 - Pearson(pred, target)``.

    Computed over pixels where BOTH are finite (same mask rule as
    :func:`masked_l1`; negatives preserved). Perfect (affine) agreement gives
    0.0; perfect anti-correlation gives 2.0.

    Degeneracy contract (pre-registered): fewer than 2 valid pixels raises
    (repo convention); zero-variance prediction or target returns the neutral
    worst score ``1.0`` as a gradient-free constant — a collapsed model is
    never rewarded, and ``train.py`` monitoring (prediction std) exposes it.
    Deterministic given identical inputs.
    """
    torch = _require_torch()
    if pred.shape != target.shape:
        raise ValueError(f"pred shape {tuple(pred.shape)} != target shape {tuple(target.shape)}")
    mask = torch.isfinite(pred) & torch.isfinite(target)
    n_valid = int(mask.sum().item())
    if n_valid < 2:
        raise ValueError("pearson_distance: fewer than 2 valid pixels")
    p = pred[mask].double()
    t = target[mask].double()
    pc = p - p.mean()
    tc = t - t.mean()
    denom = torch.sqrt((pc ** 2).sum() * (tc ** 2).sum())
    if not torch.isfinite(denom).item() or float(denom.item()) == 0.0:
        return torch.tensor(1.0), n_valid
    r = ((pc * tc).sum() / denom).clamp(-1.0, 1.0)
    loss = 1.0 - r.float()
    if not torch.isfinite(loss).item():
        raise ValueError("pearson_distance: non-finite loss")
    return loss, n_valid
