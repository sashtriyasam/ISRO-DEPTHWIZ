"""
M7 target-normalization experiment runner: frozen DA-V2-Small + lightweight head (research).

Reproducible command:

    python -m depthwizard.experiments.adapt_dav2_m7 \\
        --manifest manifests/gamus.m4.manifest.json \\
        --experiment-id dav2-gamus-head-m7-targetnorm-e01 \\
        --epochs 30 --lr 1e-3 --seed 0 --target-mode zscore \\
        --output experiments/dav2-gamus-head-m7-targetnorm-e01

Train split fits; val split selects (best val MAE); test is NEVER used here.
Writes config.json + results.json + README.md (+ JSONL log copy); head
checkpoint (*.pt, git-ignored) lives alongside for exact resumption.
"""

from __future__ import annotations

import argparse
import datetime
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np

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
            "image": np.asarray(s.image),
            "height": np.asarray(s.height, dtype=np.float32),
            "label": np.asarray(s.label).astype(np.float32) if (need_label and s.label is not None) else None,
        }
        out.append(d)
    return out


def run_adaptation(
    manifest: Path | str,
    output: Path | str,
    experiment_id: str,
    train_samples: Optional[list[str]] = None,
    val_split: str = "val",
    epochs: int = 10,
    lr: float = 1e-3,
    weight_decay: float = 0.0,
    seed: int = 0,
    device: str = "cpu",
    input_size: int = 518,
    checkpoint: Optional[Path | str] = None,
    root: Optional[Path | str] = None,
    make_visuals: bool = False,
    target_mode: str = "raw",
) -> dict[str, Any]:
    import numpy as np  # type: ignore

    manifest, out = Path(manifest), Path(output)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    set_deterministic(seed)

    train_recs = _records(manifest, "train", train_samples)
    val_recs = _records(manifest, val_split)
    if not train_recs or not val_recs:
        raise ValueError("Need non-empty train AND val selections (test never used)")
    if {r.sample_id for r in train_recs} & {r.sample_id for r in val_recs}:
        raise ValueError("Train/val sample overlap — leakage guard tripped")

    cfg = GamusConfig(root=Path(root) if root else Path("data/gamus"))
    adapter = GamusAdapter(config=GamusConfig(root=cfg.resolve_root()))
    train = _load_samples(adapter, train_recs, need_label=False)
    val = _load_samples(adapter, val_recs, need_label=True)

    backend = DepthAnythingV2Backend(checkpoint=checkpoint, device=device, input_size=input_size, seed=seed)
    backend.load()
    model = AdaptedDepthModel.from_backend(backend, input_size=input_size, seed=seed)
    params = model.parameter_report()

    # Create target scale
    if target_mode == "zscore":
        target_scale = TargetScale(mode="zscore")  # stats will be computed in train_adapted_model
    else:
        target_scale = TargetScale(mode="raw")

    summary = train_adapted_model(
        model, train, val, out, epochs=epochs, lr=lr, weight_decay=weight_decay, seed=seed,
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
    analysis["residual"] = {
        "mean": float(resid.mean()), "std": float(resid.std()),
        "p5": float(np.percentile(resid, 5)), "p95": float(np.percentile(resid, 95)),
    }

    # M3 frozen-baseline reference on the SAME val tiles (declared protocols differ).
    from depthwizard.eval.alignment import evaluate_sample as _eval_affine

    m3_vals = []
    for s, r in zip(val, val_recs):
        res = backend.infer(np.asarray(s["image"]))
        ev = _eval_affine(np.asarray(res.prediction, float), np.asarray(s["height"], float))
        m3_vals.append({"sample_id": r.sample_id, **{k: ev["aligned"].get(k) for k in ("mae", "rmse")}, "pearson": ev["pearson"], "spearman": ev["spearman"]})
    m3_ref = {
        "note": "M3 frozen relative baseline + per-image affine research eval on the same val tiles; "
        "different output semantics from M7 direct meters — NOT apples-to-apples.",
        "per_sample": m3_vals,
        "aligned_mae_mean": float(sum(v["mae"] for v in m3_vals if v["mae"] is not None) / max(1, len(m3_vals))),
    }

    results = {
        "experiment_id": experiment_id,
        "kind": f"adaptation-stage-A (frozen backbone + trainable head; target={target_mode}; research only)",
        "dataset": {
            "source": "earthflow/GAMUS",
            "manifest": manifest.as_posix(),
            "train_ids": [r.sample_id for r in train_recs],
            "val_ids": [r.sample_id for r in val_recs],
            "test_used": False,
            "target": "nDSM/AGL meters, raw, unclipped",
        },
        "model": {
            "backbone": "DepthAnythingV2-Small (frozen; requires_grad False asserted)",
            "checkpoint_id": "depth-anything/Depth-Anything-V2-Small:depth_anything_v2_vits.pth",
            "feature_tap": model.feature_tap,
            "head": "conv3x3(64->32)+BN+ReLU, conv3x3(32->16)+BN+ReLU, conv1x1(16->1), bilinear to 1024",
            "output_semantics": model.output_semantics,
            **params,
        },
        "training": {
            "loss": f"masked L1 on {'normalized' if target_mode == 'zscore' else 'raw'} meters (finite pred AND finite target; negatives kept)",
            "target_normalization": target_scale.config() if hasattr(target_scale, 'config') else {"mode": target_mode},
            "optimizer": "Adam", "lr": lr, "weight_decay": weight_decay,
            "epochs": epochs, "seed": seed, "augmentation": "none",
            "selection": "best val MAE",
            **{k: summary[k] for k in ("best_epoch", "best_value", "train_time_s")},
        },
        "validation": analysis,
        "m3_reference_same_val": m3_ref,
        "software": _software(),
        "memory": "not measured",
        "wall_time_s": time.perf_counter() - t0,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    results = json.loads(json.dumps(results, allow_nan=False, default=float))
    (out / "config.json").write_text(json.dumps({
        "experiment_id": experiment_id, "manifest": manifest.as_posix(),
        "train_samples": train_samples, "val_split": val_split, "epochs": epochs,
        "lr": lr, "weight_decay": weight_decay, "seed": seed, "device": device,
        "input_size": input_size, "checkpoint": Path(checkpoint).as_posix() if checkpoint else None,
        "root": Path(root).as_posix() if root else None,
        "target_mode": target_mode,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "README.md").write_text(
        f"# {experiment_id}\n\nFrozen DA-V2-Small + lightweight head on GAMUS with {target_mode} target normalization (research).\n"
        f"- Train ({len(train_recs)}): " + ", ".join(f"`{r.sample_id}`" for r in train_recs) + "\n"
        f"- Val ({len(val_recs)}): " + ", ".join(f"`{r.sample_id}`" for r in val_recs) + "\n"
        f"- Best val MAE: {summary['best_value']:.4f} m @ epoch {summary['best_epoch']} (selection on VAL only; test unused).\n"
        f"- Target mode: {target_mode}\n"
        f"- Output: metric GAMUS nDSM/AGL prediction (research evaluation only; not calibrated elevation).\n"
        "\nSee `config.json`, `results.json`, `log.jsonl`, `checkpoints/best.pt` (git-ignored).\n",
        encoding="utf-8",
    )
    if make_visuals:
        _visuals(out, experiment_id, model, backend, val, val_recs)
    print(f"M7 done: {experiment_id} best_val_mae={summary['best_value']:.4f} @epoch {summary['best_epoch']} -> {out}")
    return results


def _visuals(out: Path, exp_id: str, model: Any, backend: Any, val: list[dict], recs: list) -> None:
    import numpy as np  # type: ignore

    try:
        import matplotlib  # type: ignore

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as e:
        print(f"Visuals skipped ({e})")
        return
    dest = Path("outputs") / exp_id
    dest.mkdir(parents=True, exist_ok=True)
    for s, r in zip(val[:4], recs[:4]):
        rgb = np.asarray(s["image"])
        tgt = np.asarray(s["height"], float)
        pred = model.predict_height(rgb)
        rel = np.asarray(backend.infer(rgb).prediction, float)
        err = np.abs(pred - tgt)
        fig, ax = plt.subplots(1, 5, figsize=(20, 4))
        ax[0].imshow(rgb)
        ax[0].set_title(f"RGB {r.sample_id}")
        ax[1].imshow(tgt, cmap="viridis", vmin=0, vmax=45)
        ax[1].set_title("GAMUS nDSM (m)")
        ax[2].imshow(pred, cmap="viridis", vmin=0, vmax=45)
        ax[2].set_title("adapted (m)")
        ax[3].imshow(err, cmap="magma")
        ax[3].set_title("|adapted - target|")
        ax[4].imshow(rel, cmap="inferno")
        ax[4].set_title("frozen M3 relative")
        for a in ax:
            a.axis("off")
        fig.suptitle(f"{exp_id} — {r.sample_id} (diagnostic only)")
        fig.tight_layout()
        fig.savefig(dest / f"{r.sample_id}.png", dpi=80)
        plt.close(fig)
    print(f"Visuals -> {dest}")


def main() -> None:
    ap = argparse.ArgumentParser(description="M7 target-normalization adaptation experiment")
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
    ap.add_argument("--target-mode", choices=["raw", "zscore"], default="raw", help="Target normalization mode")
    args = ap.parse_args()
    file_cfg: dict = json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else {}
    run_adaptation(
        manifest=args.manifest or file_cfg.get("manifest"),
        output=args.output, experiment_id=args.experiment_id,
        train_samples=args.train_samples or file_cfg.get("train_samples"),
        val_split=args.val_split or file_cfg.get("val_split", "val"),
        epochs=args.epochs or file_cfg.get("epochs", 10),
        lr=args.lr or file_cfg.get("lr", 1e-3),
        weight_decay=args.weight_decay if args.weight_decay else file_cfg.get("weight_decay", 0.0),
        seed=args.seed if args.seed is not None else file_cfg.get("seed", 0),
        device=args.device or file_cfg.get("device", "cpu"),
        input_size=args.input_size or file_cfg.get("input_size", 518),
        checkpoint=args.checkpoint or file_cfg.get("checkpoint"),
        root=args.root or file_cfg.get("root"),
        make_visuals=args.visuals or bool(file_cfg.get("visuals", False)),
        target_mode=args.target_mode or file_cfg.get("target_mode", "raw"),
    )


if __name__ == "__main__":
    main()