"""
Masked L1 regression loss with optional target normalization (M7).

Formulation: mean |pred - target| over pixels where BOTH are finite.
Negative targets preserved (no clipping, no -5.0 special-casing).
Returns (loss_tensor, n_valid). Raises on zero valid pixels instead of
returning a fake zero loss.

TargetScale supports:
    mode="raw": identity forward/inverse (M4/M5 raw meters).
    mode="zscore": z = (y - mu) / sigma computed from TRAIN pixels only.
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
