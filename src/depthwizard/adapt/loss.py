"""
Masked L1 regression loss in raw meters (M4).

Formulation: mean |pred - target| over pixels where BOTH are finite.
Negative targets preserved (no clipping, no -5.0 special-casing).
Returns (loss_tensor, n_valid). Raises on zero valid pixels instead of
returning a fake zero loss.
"""

from __future__ import annotations

from typing import Any


class TargetScale:
    """Target representation contract. M4 uses raw meters only.

    mode="raw": identity forward/inverse (no statistics, no leakage surface).
    Any future normalized mode must compute stats from TRAIN data only and
    persist them — unknown modes raise instead of silently passing through.
    """

    def __init__(self, mode: str = "raw") -> None:
        if mode != "raw":
            raise ValueError(f"Unsupported target mode {mode!r}: M4 trains raw meters only")
        self.mode = mode

    def forward(self, target: Any) -> Any:
        return target

    def inverse(self, pred: Any) -> Any:
        return pred

    def config(self) -> dict:
        return {"mode": self.mode, "normalization": "none (raw meters)"}


def _require_torch() -> Any:
    try:
        import torch  # type: ignore
    except Exception as e:
        raise RuntimeError(f"torch is required for M4 adaptation (pip install -e .[dav2]): {e}") from e
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
