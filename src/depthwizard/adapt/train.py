"""
Deterministic training loop for the M4/M7 adaptation head (research only).

- Backbone frozen (asserted every epoch); only head parameters optimize.
- Masked L1 on raw or normalized meters; negatives preserved; no augmentation.
- Train split fits; VAL split selects (best val MAE); TEST never touched.
- Logs JSONL per epoch; saves best-val head checkpoint (git-ignored dir).
- Determinism: torch/python/numpy seeds, single-worker ordering, no shuffle
  (sorted manifest order) — reported as reproducible configuration, not
  claimed bitwise-exact across hardware.
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any, Optional

from depthwizard.adapt.loss import masked_height_weighted_l1, masked_l1, TargetScale


def set_deterministic(seed: int) -> None:
    import numpy as np  # type: ignore

    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch  # type: ignore

        torch.manual_seed(seed)
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.set_num_threads(max(1, torch.get_num_threads()))
    except Exception:
        pass


def _compute_target_stats(samples: list[dict]) -> tuple[float, float]:
    """Compute mean and std of valid target pixels from training samples.

    Uses float64 for accumulation to minimize numerical error.
    Returns (mean, std) of valid finite target pixels.
    """
    import numpy as np  # type: ignore

    all_valid = []
    for s in samples:
        h = np.asarray(s["height"], dtype=np.float64)
        mask = np.isfinite(h)
        if mask.any():
            all_valid.append(h[mask])
    if not all_valid:
        raise ValueError("No valid target pixels found in training data")
    all_vals = np.concatenate(all_valid)
    mean = float(all_vals.mean())
    std = float(all_vals.std())
    if std <= 0.0:
        raise ValueError("Target standard deviation is zero or negative")
    return mean, std


def train_one_epoch(
    model: Any,
    samples: list[dict],
    optimizer: Any,
    target_scale: TargetScale,
    out_hw: tuple[int, int] = (1024, 1024),
    height_weight: Optional[tuple[float, float]] = None,
) -> dict[str, Any]:
    """One epoch over sorted train samples (batch=1 tile; 1024px tiles).

    ``height_weight`` is None for standard masked L1, else
    ``(threshold_m, low_weight)`` for low-height-weighted masked L1 (M12):
    weights are assigned from the meter-scale target ``tgt`` while the
    comparison itself stays in the normalized space.
    """
    torch = _require_torch()
    model.assert_frozen()
    model.backbone.eval()
    model.head.train()
    total_loss, total_valid = 0.0, 0
    for s in samples:
        optimizer.zero_grad(set_to_none=True)
        pred = model.forward(s["image"], out_hw=out_hw).unsqueeze(0)  # (1,1,H,W)
        tgt = torch.as_tensor(s["height"], dtype=torch.float32).unsqueeze(0).unsqueeze(0)
        # Normalize target
        tgt_norm = target_scale.forward(tgt)
        if height_weight is None:
            loss, n_valid = masked_l1(pred, tgt_norm)
        else:
            threshold, low_weight = height_weight
            loss, n_valid = masked_height_weighted_l1(
                pred, tgt_norm, tgt, threshold=threshold, low_weight=low_weight
            )
        loss.backward()
        # Guard: backbone must not accumulate grads (frozen => no grad_fn path).
        for p in model.backbone.parameters():
            if p.grad is not None:
                raise AssertionError("Backbone received gradients — freeze violated")
        optimizer.step()
        total_loss += float(loss.item()) * n_valid
        total_valid += n_valid
    denom = max(1, total_valid)
    return {"loss": total_loss / denom, "mae": total_loss / denom, "n_valid": total_valid}


def evaluate_split(
    model: Any,
    samples: list[dict],
    target_scale: TargetScale,
    out_hw: tuple[int, int] = (1024, 1024),
) -> dict[str, Any]:
    """Validation: forward-only metric means in meters (inverse normalization applied)."""
    import numpy as np  # type: ignore

    torch = _require_torch()
    model.backbone.eval()
    model.head.eval()
    sum_abs, sum_sq, n = 0.0, 0.0, 0
    preds_all: list[Any] = []
    tgts_all: list[Any] = []
    with torch.no_grad():
        for s in samples:
            pred = model.forward(s["image"], out_hw=out_hw).detach()
            tgt = torch.as_tensor(np.asarray(s["height"], dtype=np.float32))
            pred2 = pred.squeeze(0)
            # Inverse normalize prediction to meters for metric computation
            pred_m = target_scale.inverse(pred2)
            tgt_m = tgt
            mask = torch.isfinite(pred_m) & torch.isfinite(tgt_m)
            if int(mask.sum()) == 0:
                continue
            d = (pred_m[mask] - tgt_m[mask]).double()
            sum_abs += float(d.abs().sum())
            sum_sq += float((d ** 2).sum())
            n += int(mask.sum())
            preds_all.append(np.asarray(pred_m[mask].cpu()))
            tgts_all.append(np.asarray(tgt_m[mask].cpu()))
    if n == 0:
        raise ValueError("evaluate_split: zero valid pixels")
    out = {"loss": sum_abs / n, "mae": sum_abs / n, "rmse": (sum_sq / n) ** 0.5, "n_valid": n}
    if preds_all:
        p = np.concatenate(preds_all)
        t = np.concatenate(tgts_all)
        out["pearson"] = float(np.corrcoef(p, t)[0, 1]) if p.var() and t.var() else None
    return out


def train_adapted_model(
    model: Any,
    train_samples: list[dict],
    val_samples: list[dict],
    output_dir: Path | str,
    epochs: int = 10,
    lr: float = 1e-3,
    weight_decay: float = 0.0,
    seed: int = 0,
    selection_metric: str = "mae",
    selection_mode: str = "min",
    out_hw: tuple[int, int] = (1024, 1024),
    target_scale: Optional[TargetScale] = None,
    height_weight: Optional[tuple[float, float]] = None,
) -> dict[str, Any]:
    """Full training with best-val selection. Returns summary (JSON-serializable).

    ``height_weight`` is None for standard masked L1, else
    ``(threshold_m, low_weight)`` for low-height-weighted masked L1 (M12).

    ``selection_mode`` is ``"min"`` (e.g. MAE/RMSE) or ``"max"`` (e.g. Pearson
    for M16 structural selection). Pearson is affine-invariant, so maximizing
    pooled direct Pearson selects the same structure as the affine protocol.
    """
    torch = _require_torch()
    set_deterministic(seed)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    ckpt_dir = out / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)

    # Compute target normalization stats from TRAIN data only (no leakage).
    if target_scale is None:
        # Default to raw meters (M4/M5 behavior)
        target_scale = TargetScale(mode="raw")
    elif target_scale.mode == "zscore" and (target_scale.mu == 0.0 and target_scale.sigma == 1.0):
        # Compute stats from train data if not provided
        mean, std = _compute_target_stats(train_samples)
        target_scale = TargetScale(mode="zscore", mu=mean, sigma=std)

    optimizer = torch.optim.Adam([p for p in model.head.parameters() if p.requires_grad], lr=lr, weight_decay=weight_decay)
    if selection_mode not in ("min", "max"):
        raise ValueError(f"selection_mode must be 'min' or 'max', got {selection_mode!r}")
    log_path = out / "log.jsonl"
    best = {"epoch": -1, "value": float("-inf") if selection_mode == "max" else float("inf")}
    history: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    with log_path.open("w", encoding="utf-8") as logf:
        for epoch in range(epochs):
            tr = train_one_epoch(
                model, train_samples, optimizer, target_scale,
                out_hw=out_hw, height_weight=height_weight,
            )
            va = evaluate_split(model, val_samples, target_scale, out_hw=out_hw)
            row = {
                "epoch": epoch,
                "train_loss": tr["loss"],
                "train_mae": tr["mae"],
                "val_loss": va["loss"],
                "val_mae": va["mae"],
                "val_rmse": va["rmse"],
                "val_pearson": va.get("pearson"),
                "lr": float(optimizer.param_groups[0]["lr"]),
                "n_train_valid": tr["n_valid"],
                "n_val_valid": va["n_valid"],
            }
            logf.write(json.dumps(row, sort_keys=True) + "\n")
            logf.flush()
            history.append(row)
            key = va.get(selection_metric)
            if key is not None and (
                float(key) < best["value"] if selection_mode == "min"
                else float(key) > best["value"]
            ):
                best = {"epoch": epoch, "value": float(key)}
                model.save_head(ckpt_dir / "best.pt", extra={"epoch": epoch, selection_metric: float(key)})
    # Restore best-val head for downstream evaluation.
    model.load_head(ckpt_dir / "best.pt")
    summary = {
        "epochs": epochs,
        "lr": lr,
        "weight_decay": weight_decay,
        "seed": seed,
        "selection_metric": selection_metric,
        "selection_mode": selection_mode,
        "best_epoch": best["epoch"],
        "best_value": best["value"],
        "history": history,
        "train_time_s": time.perf_counter() - t0,
        "target_scale": target_scale.config(),
        "height_weight": (
            {"threshold_m": float(height_weight[0]), "low_weight": float(height_weight[1])}
            if height_weight is not None else None
        ),
    }
    (out / "train_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def _require_torch() -> Any:
    try:
        import torch  # type: ignore
    except Exception as e:
        raise RuntimeError(f"torch is required for M4/M7 adaptation (pip install -e .[dav2]): {e}") from e
    return torch