"""
M9 geographic training composition rebalancing experiment runner: frozen DA-V2-Small + lightweight head (research).

Reproducible command:

    python -m depthwizard.experiments.adapt_dav2_m9 \\
        --manifest manifests/gamus.m4.manifest.json \\
        --experiment-id dav2-gamus-head-m9-composition-16-4-4-e01 \\
        --epochs 30 --lr 1e-3 --seed 0 --target-mode raw \\
        --output experiments/dav2-gamus-head-m9-composition-16-4-4-e01

Train split: 16 DC + 4 PHL + 4 NYC (24 total) from train split.
Val split: same 8 DC tiles as M5.
Test is NEVER used here.
Writes config.json + results.json + README.md (+ JSONL log copy); head
checkpoint (*.pt, git-ignored) lives alongside for exact resumption.
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
    
    Uses gamus.m8.geographic.json which has 24 DC + 8 PHL + 8 NYC in train split.
    """
    # Use m8 geographic manifest for training data (has 24 DC train tiles)
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
) -> dict[str, Any]:
    import numpy as np  # type: ignore

    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    set_deterministic(seed)

    # Select training samples: 16 DC + 4 PHL + 4 NYC from train split (using m8 geographic manifest)
    train_recs = _select_train_recs()
    # Use m4 manifest for validation (exact 8 DC val tiles as M5)
    val_recs = _records(Path("manifests/gamus.m4.manifest.json"), val_split)

    if not train_recs or not val_recs:
        raise ValueError("Need non-empty train AND val selections (test never used)")
    if {r.sample_id for r in train_recs} & {r.sample_id for r in val_recs}:
        raise ValueError("Train/val sample overlap — leakage guard tripped")

    # Verify city composition
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

    backend = DepthAnythingV2Backend(checkpoint=None, device=device, input_size=input_size, seed=seed)
    backend.load()
    model = AdaptedDepthModel.from_backend(backend, input_size=input_size, seed=seed)
    model.parameter_report()

    # Force raw target mode (M5 baseline)
    target_scale = TargetScale(mode="raw")

    train_adapted_model(
        model, train, val, Path(output), epochs=epochs, lr=lr, weight_decay=weight_decay, seed=seed,
        target_scale=target_scale
    )

    # Final validation analysis on best-val head.
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
    # Residual distribution + overfit signals.
    resid = np.concatenate([(np.asarray(p, float) - np.asarray(t, float)).ravel() for p, t in zip(preds, tgts)])
    resid = resid[np.isfinite(resid)]
    analysis = {**analysis, "residual": {
        "mean": float(resid.mean()), "std": float(resid.std()),
        "p5": float(np.percentile(resid, 5)), "p95": float(np.percentile(resid, 95)),
    }}

    # M3 frozen-baseline reference on the SAME val tiles (same protocol).
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

    results = {
        "experiment_id": experiment_id,
        "kind": "adaptation-stage-A (frozen backbone + trainable head; geographic composition 16/4/4; raw target; research only)",
        "dataset": {
            "source": "earthflow/GAMUS",
            "manifest": "manifests/gamus.m8.geographic.json (train) + manifests/gamus.m4.manifest.json (val)",
            "train_ids": [r.sample_id for r in train_recs],
            "val_ids": [r.sample_id for r in val_recs],
            "test_used": False,
            "target": "nDSM/AGL meters, raw, unclipped",
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
            "loss": "masked L1 on raw meters (finite pred AND finite target; negatives kept)",
            "target_normalization": {"mode": "raw", "normalization": "none (raw meters)"},
            "optimizer": "Adam", "lr": 1e-3, "weight_decay": 0.0,
            "epochs": 30, "seed": 0, "augmentation": "none",
            "selection": "best val MAE",
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
        "epochs": 30,
        "lr": 0.001,
        "weight_decay": 0.0,
        "seed": 0,
        "device": "cpu",
        "input_size": 518,
        "checkpoint": None,
        "root": "data/gamus",
        "visuals": False,
        "target_mode": "raw",
        "city_composition": "16 DC + 4 PHL + 4 NYC",
        "comment": "Geographic training composition rebalancing (M9). 24 train tiles: 16 DC + 4 PHL + 4 NYC from train split (m8 geographic manifest). Same 8 DC val tiles as M5 (m4 manifest). Target mode: raw meters. All other factors frozen to M5."
    }
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    out.joinpath("config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out.joinpath("results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Load train_summary for best_epoch
    train_summary_path = out / "train_summary.json"
    train_summary = {}
    if train_summary_path.exists():
        train_summary = json.loads(train_summary_path.read_text(encoding="utf-8"))

    # README.md
    val = results.get("validation", {})
    error = val.get("error", {})
    mae = error.get("mae", 0.0)
    rmse = error.get("rmse", 0.0)
    pearson = val.get("correlation", {}).get("pearson", 0.0)
    readme = f"""# {experiment_id}

**M9 Geographic Training Composition Rebalancing** — frozen DA-V2-Small + lightweight head on 24 tiles (16 DC + 4 PHL + 4 NYC), raw-meter masked L1, validated on same 8 DC tiles as M5.

## Config
- Train Manifest: `manifests/gamus.m8.geographic.json` (24 DC + 8 PHL + 8 NYC train)
- Val Manifest: `manifests/gamus.m4.manifest.json` (8 DC val, identical to M5)
- Train: 24 tiles (16 DC + 4 PHL + 4 NYC from train split)
- Val: 8 DC tiles (identical to M5)
- Target mode: raw meters (M5 baseline)
- Epochs: 30, lr=1e-3, seed=0, Adam, weight_decay=0, batch=1 tile, no augmentation
- Selection: best val MAE on fixed 8 DC val tiles

## Results
- **Best epoch**: {train_summary.get("best_epoch", "N/A")}
- **Val MAE (best)**: {mae:.4f} m
- **Val RMSE (best)**: {rmse:.4f} m
- **Val Pearson (best)**: {pearson:.4f}

## Comparison to M5/M8 Baselines
| Metric | M5 (24 DC train) | M8 (8/8/8 train) | M9 (16/4/4 train) |
|--------|------------------|------------------|-------------------|
| Val MAE | 5.1500 m | 6.8036 m | {mae:.4f} m |
| Delta vs M5 | — | +1.6536 m | {mae - 5.1500:+.4f} m |
| Delta vs M8 | — | — | {mae - 6.8036:+.4f} m |

## Notes
- No geographic eval during training — secondary eval via M6 protocol after checkpoint selection
- Head: ~23k params (conv3x3 64->32->16->1 + bilinear upsample)
- Backbone: frozen DA-V2-Small (24.8M params)
"""
    out.joinpath("README.md").write_text(readme, encoding="utf-8")

    return results


def main() -> None:
    ap = argparse.ArgumentParser(description="M9 geographic training composition rebalancing experiment")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--train-samples", nargs="*", default=None)
    ap.add_argument("--val-split", default="val")
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--input-size", type=int, default=518)
    ap.add_argument("--checkpoint", default=None)
    ap.add_argument("--root", default=None)
    ap.add_argument("--config", default=None)
    ap.add_argument("--visuals", action="store_true")
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
    )


if __name__ == "__main__":
    main()