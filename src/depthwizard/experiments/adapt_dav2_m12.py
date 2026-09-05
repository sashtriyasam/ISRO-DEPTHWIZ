"""
M12 low-height-weighted loss on M10 recipe runner: frozen DA-V2-Small + lightweight head (research).

Reproducible command:

    python -m depthwizard.experiments.adapt_dav2_m12 \\
        --manifest manifests/gamus.m8.geographic.json \\
        --experiment-id dav2-gamus-head-m12-lowheight-loss-e01 \\
        --epochs 30 --lr 1e-3 --seed 0 --target-mode zscore \\
        --output experiments/dav2-gamus-head-m12-lowheight-loss-e01

Train split: 16 DC + 4 PHL + 4 NYC (24 total) — EXACT M10/M9 train IDs.
Val split: same 8 DC tiles as M5/M8/M9/M10/M11.
Test is NEVER used here.
Writes config.json + results.json + README.md (+ JSONL log copy); head
checkpoint (*.pt, git-ignored) lives alongside for exact resumption.

Single-factor change vs M10: loss formulation only —
masked L1 in z-score space -> low-height-weighted masked L1 in z-score
space (2x weight for meter targets < 5.0 m, 1x otherwise). Weights are
assigned from the ORIGINAL METER target before z-score conversion; the
comparison itself stays in z-space. All other factors frozen to M10.
"""

from __future__ import annotations

import argparse
import datetime
import json
import platform
import sys
from pathlib import Path
from typing import Any, Optional

from depthwizard.adapt.evaluate import evaluate_predictions
from depthwizard.adapt.loss import TargetScale
from depthwizard.adapt.model import AdaptedDepthModel
from depthwizard.adapt.train import set_deterministic, train_adapted_model
from depthwizard.data.adapter import GamusAdapter
from depthwizard.data.config import GamusConfig
from depthwizard.data.manifest import load_manifest
from depthwizard.data.schemas import GAMUS_CLASSES, GamusRecord, canonical_split
from depthwizard.depth.depth_anything_v2 import DepthAnythingV2Backend

# Pre-registered M12 loss constants (fixed; NOT tuned after seeing results).
HEIGHT_THRESHOLD_M = 5.0
LOW_HEIGHT_WEIGHT = 2.0


def _software() -> dict[str, str]:
    def _v(mod: str) -> str:
        try:
            m = __import__(mod)
            return getattr(m, "__version__", "installed")
        except Exception:
            return "not installed"

    out = {"python": sys.version.split()[0], "platform": platform.platform()}
    for mod in ("torch", "torchvision", "numpy", "h5py", "cv2", "PIL"):
        out[mod] = _v(mod)
    try:
        import torch  # type: ignore
        out["cuda_available"] = str(torch.cuda.is_available())
    except Exception:
        out["cuda_available"] = "unknown"
    return out


def _records(manifest: Path, split: str, sample_ids: Optional[list[str]] = None) -> list[GamusRecord]:
    from depthwizard.data.schemas import GAMUS_SPLITS

    data = load_manifest(manifest)
    recs = [GamusRecord.from_dict(d) for d in data.get("records", []) if GamusRecord.from_dict(d).split == canonical_split(split)]
    if sample_ids:
        recs = [r for r in recs if r.sample_id in set(sample_ids)]
    order = {s: i for i, s in enumerate(GAMUS_SPLITS)}
    recs.sort(key=lambda r: (order.get(r.split, 99), r.sample_id))
    return recs


def _load_samples(adapter: GamusAdapter, recs: list[GamusRecord], need_label: bool) -> list[dict]:
    import numpy as np  # type: ignore

    out = []
    for r in recs:
        s = adapter.to_sample(r, load_arrays=True)
        if s.image is None or s.height is None:
            raise FileNotFoundError(f"Missing modality for '{r.sample_id}'")
        d: dict[str, Any] = {
            "sample_id": r.sample_id,
            "split": r.split,
            "city": r.sample_id.split('_')[0],
            "image": np.asarray(s.image),
            "height": np.asarray(s.height, dtype=np.float32),
            "label": np.asarray(s.label).astype(np.float32) if (need_label and s.label is not None) else None,
        }
        out.append(d)
    return out


def _select_train_recs() -> list[GamusRecord]:
    """Select 16 DC + 4 PHL + 4 NYC samples from train split deterministically.

    Identical to M9/M10: uses gamus.m8.geographic.json which has
    24 DC + 8 PHL + 8 NYC in train split. First-N sorted sample_ids per city.
    """
    data = load_manifest(Path("manifests/gamus.m8.geographic.json"))
    all_train_recs = [GamusRecord.from_dict(d) for d in data.get("records", []) if GamusRecord.from_dict(d).split == "train"]
    by_city: dict[str, list[GamusRecord]] = {}
    for r in all_train_recs:
        city = r.sample_id.split('_')[0]
        by_city.setdefault(city, []).append(r)
    selected = []
    for city, count in [("DC", 16), ("PHL", 4), ("NYC", 4)]:
        city_recs = by_city.get(city, [])
        city_recs.sort(key=lambda r: r.sample_id)
        selected.extend(city_recs[:count])
    if len(selected) != 24:
        raise ValueError(f"Expected 24 train samples, got {len(selected)}")
    city_counts = {}
    for r in selected:
        city = r.sample_id.split('_')[0]
        city_counts[city] = city_counts.get(city, 0) + 1
    expected = {"DC": 16, "PHL": 4, "NYC": 4}
    if city_counts != expected:
        raise ValueError(f"Unexpected train city composition: {city_counts}, expected {expected}")
    return selected


def _train_target_stats(train: list[dict]) -> dict[str, Any]:
    """Extended train-only target statistics (finite pixels, negatives kept).

    Mean/std match the training-time computation (float64 accumulation).
    Records n, min, max, and the <5m / >=5m valid-pixel split used by the
    M12 loss weighting for metadata. No validation pixels involved.
    """
    import numpy as np  # type: ignore

    vals = []
    n_neg = 0
    for s in train:
        h = np.asarray(s["height"], dtype=np.float64)
        m = np.isfinite(h)
        if m.any():
            v = h[m]
            vals.append(v)
            n_neg += int((v < 0).sum())
    if not vals:
        raise ValueError("No valid target pixels found in training data")
    allv = np.concatenate(vals)
    n_low = int((allv < HEIGHT_THRESHOLD_M).sum())
    return {
        "n_valid_pixels": int(allv.size),
        "n_negative_pixels": int(n_neg),
        "n_below_threshold": n_low,
        "n_at_or_above_threshold": int(allv.size) - n_low,
        "mu": float(allv.mean()),
        "sigma": float(allv.std()),
        "min": float(allv.min()),
        "max": float(allv.max()),
    }


def run_adaptation(
    manifest: Path | str,
    output: Path | str,
    experiment_id: str,
    train_samples: Optional[list[str]] = None,
    val_split: str = "val",
    epochs: int = 30,
    lr: float = 1e-3,
    weight_decay: float = 0.0,
    seed: int = 0,
    device: str = "cpu",
    input_size: int = 518,
    checkpoint: Optional[Path | str] = None,
    root: Optional[Path | str] = None,
    make_visuals: bool = False,
    target_mode: str = "zscore",
) -> dict[str, Any]:
    import numpy as np  # type: ignore

    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    set_deterministic(seed)

    # Select training samples: EXACT M10/M9 set (16 DC + 4 PHL + 4 NYC).
    train_recs = _select_train_recs()
    # Use m4 manifest for validation (exact 8 DC val tiles as M5/M8/M9/M10).
    val_recs = _records(Path("manifests/gamus.m4.manifest.json"), val_split)

    if not train_recs or not val_recs:
        raise ValueError("Need non-empty train AND val selections (test never used)")
    if {r.sample_id for r in train_recs} & {r.sample_id for r in val_recs}:
        raise ValueError("Train/val sample overlap — leakage guard tripped")

    # Verify city composition (must equal M10 exactly).
    city_counts = {}
    for r in train_recs:
        city = r.sample_id.split('_')[0]
        city_counts[city] = city_counts.get(city, 0) + 1
    expected = {"DC": 16, "PHL": 4, "NYC": 4}
    if city_counts != expected:
        raise ValueError(f"Unexpected train city composition: {city_counts}, expected {expected}")

    cfg = GamusConfig(root=Path("data/gamus"))
    adapter = GamusAdapter(config=GamusConfig(root=cfg.resolve_root()))
    train = _load_samples(adapter, train_recs, need_label=False)
    val = _load_samples(adapter, val_recs, need_label=True)

    # Extended train-only stats for metadata (pre-training, no leakage).
    stats_meta = _train_target_stats(train)

    backend = DepthAnythingV2Backend(checkpoint=None, device=device, input_size=input_size, seed=seed)
    backend.load()
    model = AdaptedDepthModel.from_backend(backend, input_size=input_size, seed=seed)
    model.parameter_report()

    # zscore target mode, statistics computed from TRAIN pixels only inside
    # train_adapted_model (no caller-supplied values; M7 values NOT reused).
    if target_mode != "zscore":
        raise ValueError(f"M12 requires target_mode='zscore', got {target_mode!r}")
    target_scale = TargetScale(mode="zscore")

    # Single-factor change vs M10: low-height-weighted masked L1.
    summary = train_adapted_model(
        model, train, val, Path(output), epochs=epochs, lr=lr, weight_decay=weight_decay, seed=seed,
        target_scale=target_scale,
        height_weight=(HEIGHT_THRESHOLD_M, LOW_HEIGHT_WEIGHT),
    )

    # Apply the FITTED train-only z-score scale to the model before final
    # validation analysis so predict_height() inverse-transforms to meters.
    fitted = summary.get("target_scale", {})
    model.target_scale = TargetScale(mode="zscore", mu=float(fitted["mu"]), sigma=float(fitted["sigma"]))

    # Final validation analysis on best-val head (meters).
    preds, tgts, labels = [], [], []
    for s in val:
        preds.append(model.predict_height(s["image"]))
        tgts.append(np.asarray(s["height"], dtype=np.float64))
        labels.append(np.asarray(s["label"]) if s["label"] is not None else np.full_like(tgts[-1], np.nan))
    has_label = [lab for lab in labels if np.isfinite(np.asarray(lab, dtype=np.float64)).any()]
    analysis = evaluate_predictions(
        preds, tgts,
        labels=[np.asarray(lab) for lab in labels] if len(has_label) == len(labels) else None,
        class_names=dict(GAMUS_CLASSES),
    )
    resid = np.concatenate([(np.asarray(p, float) - np.asarray(t, float)).ravel() for p, t in zip(preds, tgts)])
    resid = resid[np.isfinite(resid)]
    analysis = {**analysis, "residual": {
        "mean": float(resid.mean()), "std": float(resid.std()),
        "p5": float(np.percentile(resid, 5)), "p95": float(np.percentile(resid, 95)),
    }}

    # M3 frozen-baseline reference on the SAME val tiles (same protocol note as M10).
    from depthwizard.eval.alignment import evaluate_sample as _eval_affine

    backend_m3 = DepthAnythingV2Backend(checkpoint=None, device="cpu", input_size=518, seed=0)
    backend_m3.load()
    m3_vals = []
    for s, r in zip(val, val_recs):
        res = backend_m3.infer(np.asarray(s["image"]))
        ev = _eval_affine(np.asarray(res.prediction, float), np.asarray(s["height"], float))
        m3_vals.append({"sample_id": r.sample_id, **{k: ev["aligned"].get(k) for k in ("mae", "rmse")}, "pearson": ev["pearson"], "spearman": ev["spearman"]})
    m3_ref = {
        "note": "M3 frozen relative baseline + per-image affine research eval on the same val tiles; different output semantics — NOT apples-to-apples.",
        "per_sample": m3_vals,
        "aligned_mae_mean": float(sum(v["mae"] for v in m3_vals if v["mae"] is not None) / max(1, len(m3_vals))),
    }

    loss_desc = (
        f"low-height-weighted masked L1 in z-score space "
        f"(weight {LOW_HEIGHT_WEIGHT}x for meter target < {HEIGHT_THRESHOLD_M} m, "
        f"1x otherwise; weights from meter targets, comparison in z-space; "
        f"finite pred AND finite target; negatives kept; metrics inverse-transformed to meters)"
    )
    results = {
        "experiment_id": experiment_id,
        "kind": "adaptation-stage-A (frozen backbone + trainable head; geographic composition 16/4/4; zscore target train-only; low-height-weighted L1; research only)",
        "dataset": {
            "source": "earthflow/GAMUS",
            "manifest": "manifests/gamus.m8.geographic.json (train) + manifests/gamus.m4.manifest.json (val)",
            "train_ids": [r.sample_id for r in train_recs],
            "val_ids": [r.sample_id for r in val_recs],
            "test_used": False,
            "target": "nDSM/AGL meters, raw, unclipped (z-score normalized for loss; metrics inverse-transformed to meters)",
            "city_composition": {
                "train": {"DC": 16, "PHL": 4, "NYC": 4},
                "val": {"DC": 8}
            }
        },
        "model": {
            "backbone": "DepthAnythingV2-Small (frozen; requires_grad False asserted)",
            "checkpoint_id": "depth-anything/Depth-Anything-V2-Small:depth_anything_v2_vits.pth",
            "feature_tap": "depth_head.scratch.output_conv1",
            "head": "conv3x3(64->32)+BN+ReLU, conv3x3(32->16)+BN+ReLU, conv1x1(16->1), bilinear to 1024",
            "output_semantics": "gamus-ndsm-agl-metric (research evaluation only; not calibrated elevation)",
            "backbone_total": 24785089,
            "head_total": 23201,
            "head_trainable": 23201,
            "total": 24808290,
            "trainable": 23201,
        },
        "training": {
            "loss": loss_desc,
            "loss_weighting": {
                "threshold_m": HEIGHT_THRESHOLD_M,
                "low_weight": LOW_HEIGHT_WEIGHT,
                "high_weight": 1.0,
            },
            "target_normalization": {
                "mode": "zscore",
                "mu": float(fitted["mu"]),
                "sigma": float(fitted["sigma"]),
                "normalization": "zscore (train pixels only)",
                "n_valid_pixels": stats_meta["n_valid_pixels"],
                "n_negative_pixels": stats_meta["n_negative_pixels"],
                "n_below_threshold": stats_meta["n_below_threshold"],
                "n_at_or_above_threshold": stats_meta["n_at_or_above_threshold"],
                "min": stats_meta["min"],
                "max": stats_meta["max"],
            },
            "optimizer": "Adam", "lr": lr, "weight_decay": weight_decay,
            "epochs": epochs, "seed": seed, "augmentation": "none",
            "selection": "best val MAE (meters)",
        },
        "validation": analysis,
        "m3_reference_same_val": m3_ref,
        "software": _software(),
        "memory": "not measured",
        "wall_time_s": 0.0,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    config = {
        "experiment_id": experiment_id,
        "manifest": "manifests/gamus.m8.geographic.json (train) + manifests/gamus.m4.manifest.json (val)",
        "train_samples": None,
        "val_split": "val",
        "epochs": epochs,
        "lr": lr,
        "weight_decay": weight_decay,
        "seed": seed,
        "device": "cpu",
        "input_size": 518,
        "checkpoint": None,
        "root": "data/gamus",
        "visuals": False,
        "target_mode": "zscore",
        "loss_mode": "low-height-weighted",
        "loss_threshold_m": HEIGHT_THRESHOLD_M,
        "loss_low_weight": LOW_HEIGHT_WEIGHT,
        "city_composition": "16 DC + 4 PHL + 4 NYC",
        "comment": "Low-height-weighted loss on M10 recipe (M12). 24 train tiles: 16 DC + 4 PHL + 4 NYC (EXACT M10 IDs). Same 8 DC val tiles. ONLY change vs M10: masked L1 -> low-height-weighted masked L1 (2x below 5 m). All other factors frozen.",
    }
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    out.joinpath("config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out.joinpath("results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # README.md (uses captured summary + fitted stats).
    val = results.get("validation", {})
    error = val.get("error", {})
    mae = error.get("mae", 0.0)
    rmse = error.get("rmse", 0.0)
    pearson = val.get("correlation", {}).get("pearson", 0.0)
    mu = float(fitted["mu"])
    sigma = float(fitted["sigma"])
    readme = f"""# {experiment_id}

**M12 Low-Height-Weighted Loss on M10 Recipe** — frozen DA-V2-Small + lightweight head on 24 tiles (16 DC + 4 PHL + 4 NYC, EXACT M10 IDs), low-height-weighted masked L1 in z-score space (train-only statistics), validated on same 8 DC tiles as M5/M8/M9/M10/M11. Metrics in meters (inverse-transformed).

## Config
- Train Manifest: `manifests/gamus.m8.geographic.json` (EXACT M10 train IDs)
- Val Manifest: `manifests/gamus.m4.manifest.json` (8 DC val, identical to M5/M8/M9/M10/M11)
- Train: 24 tiles (16 DC + 4 PHL + 4 NYC)
- Val: 8 DC tiles (identical to M5/M8/M9/M10/M11)
- Target mode: zscore (train-only mu={mu:.4f}, sigma={sigma:.4f}, n={stats_meta["n_valid_pixels"]})
- Loss: low-height-weighted masked L1 (2x for meter target < 5.0 m, 1x otherwise)
- Epochs: {epochs}, lr={lr}, seed={seed}, Adam, weight_decay={weight_decay}, batch=1 tile, no augmentation
- Selection: best val MAE (meters) on fixed 8 DC val tiles

## Results
- **Best epoch**: {summary.get("best_epoch", "N/A")}
- **Val MAE (best)**: {mae:.4f} m
- **Val RMSE (best)**: {rmse:.4f} m
- **Val Pearson (best)**: {pearson:.4f}

## Comparison (same 8 DC val tiles)
| Metric | M10 seed0 (zscore L1) | M11 mean (zscore L1) | M12 (weighted L1) |
|--------|----------------------|---------------------|-------------------|
| Val MAE | 5.8204 m | 5.7428 m | {mae:.4f} m |
| Delta vs M11 mean | — | — | {mae - 5.7428:+.4f} m |
| Delta vs M10 seed0 | — | -0.0776 m | {mae - 5.8204:+.4f} m |

## Notes
- ONLY change vs M10: loss formulation (masked L1 -> low-height-weighted masked L1).
- Weights from meter-scale targets; comparison stays in z-space; negatives kept.
- Head: ~23k params; backbone frozen DA-V2-Small (24.8M params).
- No geographic eval during training — secondary eval via M6 protocol after checkpoint selection.
"""
    out.joinpath("README.md").write_text(readme, encoding="utf-8")

    return results


def main() -> None:
    ap = argparse.ArgumentParser(description="M12 low-height-weighted loss on M10 recipe experiment")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--train-samples", nargs="*", default=None)
    ap.add_argument("--val-split", default="val")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--input-size", type=int, default=518)
    ap.add_argument("--checkpoint", default=None)
    ap.add_argument("--root", default=None)
    ap.add_argument("--config", default=None)
    ap.add_argument("--visuals", action="store_true")
    ap.add_argument("--target-mode", choices=["raw", "zscore"], default="zscore")
    args = ap.parse_args()
    file_cfg: dict = json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else {}
    run_adaptation(
        manifest=args.manifest or file_cfg.get("manifest"),
        output=args.output, experiment_id=args.experiment_id,
        train_samples=args.train_samples or file_cfg.get("train_samples"),
        val_split=args.val_split or file_cfg.get("val_split", "val"),
        epochs=args.epochs or file_cfg.get("epochs", 30),
        lr=args.lr or file_cfg.get("lr", 1e-3),
        weight_decay=args.weight_decay if args.weight_decay else file_cfg.get("weight_decay", 0.0),
        seed=args.seed if args.seed is not None else file_cfg.get("seed", 0),
        device=args.device or file_cfg.get("device", "cpu"),
        input_size=args.input_size or file_cfg.get("input_size", 518),
        checkpoint=args.checkpoint or file_cfg.get("checkpoint"),
        root=args.root or file_cfg.get("root"),
        make_visuals=args.visuals or bool(file_cfg.get("visuals", False)),
        target_mode=args.target_mode or file_cfg.get("target_mode", "zscore"),
    )


if __name__ == "__main__":
    main()
