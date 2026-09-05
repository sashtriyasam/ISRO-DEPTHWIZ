"""
M6 Geographic Validation: frozen M5 adapted DA-V2-Small evaluation across cities.

Evaluates the frozen M5 checkpoint (epoch 23, best val MAE) on a geographically
diverse manifest. No training, no fine-tuning, no model changes.

Reproduces M5's direct-metric evaluation protocol on a per-city basis.

Reproducible command:

    python -m depthwizard.experiments.m6_geographic \\
        --manifest manifests/gamus.m6.geographic.json \\
        --checkpoint experiments/dav2-gamus-head-m5-e01/checkpoints/best.pt \\
        --output experiments/m6-geographic-eval
"""

from __future__ import annotations

import argparse
import datetime
import json
import platform
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Optional

import numpy as np
import torch

from depthwizard.adapt.evaluate import evaluate_predictions
from depthwizard.adapt.model import AdaptedDepthModel
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


def _records(manifest: Path, splits: Optional[list[str]] = None, city_filter: Optional[str] = None) -> list[GamusRecord]:
    data = load_manifest(manifest)
    recs = [GamusRecord.from_dict(d) for d in data.get("records", [])]
    if splits:
        recs = [r for r in recs if r.split in {canonical_split(s) for s in splits}]
    if city_filter:
        recs = [r for r in recs if r.sample_id.split('_')[0] == city_filter]
    from depthwizard.data.schemas import GAMUS_SPLITS
    order = {s: i for i, s in enumerate(GAMUS_SPLITS)}
    recs.sort(key=lambda r: (order.get(r.split, 99), r.sample_id))
    return recs


def _load_samples(adapter: GamusAdapter, recs: list[GamusRecord]) -> list[dict]:
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
            "height": np.asarray(s.height, dtype=np.float64),
            "label": np.asarray(s.label).astype(np.float32) if s.label is not None else None,
        }
        out.append(d)
    return out


def run_geographic_validation(
    manifest: Path | str,
    base_checkpoint: Path | str,
    adapt_checkpoint: Path | str,
    output: Path | str,
    device: str = "cpu",
    input_size: int = 518,
    seed: int = 0,
    splits: Optional[list[str]] = None,
    make_visuals: bool = False,
    target_mu: Optional[float] = None,
    target_sigma: Optional[float] = None,
) -> dict[str, Any]:
    manifest = Path(manifest)
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    # Load frozen adapted checkpoint (M5/M8/M9/M10 head)
    backend = DepthAnythingV2Backend(checkpoint=base_checkpoint, device=device, input_size=input_size, seed=seed)
    backend.load()
    model = AdaptedDepthModel.from_backend(backend, input_size=input_size, seed=seed)
    # Load only the head state from adaptation best checkpoint
    payload = torch.load(str(adapt_checkpoint), map_location="cpu", weights_only=False)
    model.head.load_state_dict(payload["head_state"])
    # Optional z-score target scale (e.g. M10): inverse-transform predictions to
    # meters using TRAIN-derived statistics. Default raw preserves legacy behavior.
    if target_mu is not None or target_sigma is not None:
        if target_mu is None or target_sigma is None:
            raise ValueError("Both target_mu and target_sigma are required for z-score geographic eval")
        from depthwizard.adapt.loss import TargetScale
        model.target_scale = TargetScale(mode="zscore", mu=float(target_mu), sigma=float(target_sigma))
    model.assert_frozen()
    params = model.parameter_report()

    # Load geographic manifest
    cfg = GamusConfig(root=Path("data/gamus"))
    adapter = GamusAdapter(config=GamusConfig(root=cfg.resolve_root()))

    # Group records by city
    if splits is None:
        splits = ["val", "test"]
    recs = _records(manifest, splits=splits)
    if not recs:
        raise ValueError("No records selected")

    cities = sorted({r.sample_id.split('_')[0] for r in recs})
    print(f"Evaluating {len(recs)} samples across {len(cities)} cities: {cities}")

    # Per-city evaluation
    city_results: dict[str, Any] = {}
    all_preds, all_tgts, all_labels = [], [], []

    for city in cities:
        city_recs = [r for r in recs if r.sample_id.split('_')[0] == city]
        city_samples = _load_samples(adapter, city_recs)
        preds, tgts, labels = [], [], []
        for s in city_samples:
            preds.append(model.predict_height(s["image"]))
            tgts.append(np.asarray(s["height"], dtype=np.float64))
            labels.append(np.asarray(s["label"]) if s["label"] is not None else np.full_like(tgts[-1], np.nan))

        # Per-city analysis
        analysis = evaluate_predictions(
            preds, tgts,
            labels=[np.asarray(l) for l in labels],
            class_names=dict(GAMUS_CLASSES),
        )
        analysis["n_samples"] = len(city_recs)
        analysis["split_distribution"] = dict(Counter(r.split for r in city_recs))
        city_results[city] = analysis

        all_preds.extend(preds)
        all_tgts.extend(tgts)
        all_labels.extend(labels)

    # Aggregate across cities
    macro_mae = np.mean([v["error"]["mae"] for v in city_results.values() if v["error"]["mae"] is not None])
    macro_rmse = np.mean([v["error"]["rmse"] for v in city_results.values() if v["error"]["rmse"] is not None])

    # Micro (pixel-weighted) aggregate
    all_p = np.concatenate([np.asarray(p).ravel() for p in all_preds])
    all_t = np.concatenate([np.asarray(t).ravel() for t in all_tgts])
    mask = np.isfinite(all_p) & np.isfinite(all_t)
    pv, tv = all_p[mask], all_t[mask]
    micro_mae = float(np.abs(pv - tv).mean())
    micro_rmse = float(np.sqrt(((pv - tv) ** 2).mean()))

    # Cross-city gap (macro - in-city if DC is reference)
    in_city_mae = city_results.get("DC", {}).get("error", {}).get("mae")
    cross_cities = [c for c in cities if c != "DC"]
    cross_mae = np.mean([city_results[c]["error"]["mae"] for c in cross_cities if city_results[c]["error"]["mae"] is not None]) if cross_cities else None
    gap = (cross_mae - in_city_mae) if (cross_mae is not None and in_city_mae is not None) else None

    # M5 reference (same-city DC val from M5)
    m5_ref = {
        "note": "M5 best val MAE on DC val (8 samples, direct meters, frozen M5 head)",
        "val_mae": 5.1500,
        "val_rmse": 7.3685,
        "pearson": 0.6310,
        "spearman": 0.5861,
    }

    results = {
        "experiment_id": "m6-geographic-validation",
        "kind": "geographic validation of frozen M5 adapted model (no training)",
        "dataset": {
            "source": "earthflow/GAMUS",
            "manifest": manifest.as_posix(),
            "splits": splits,
            "cities": cities,
            "city_counts": {c: len([r for r in recs if r.sample_id.split('_')[0] == c]) for c in cities},
            "target": "nDSM/AGL meters, raw, unclipped",
        },
        "model": {
            "backbone": "DepthAnythingV2-Small (frozen)",
            "checkpoint": "depth-anything/Depth-Anything-V2-Small:depth_anything_v2_vits.pth",
            "adaptation_checkpoint": str(Path("experiments/dav2-gamus-head-m5-e01/checkpoints/best.pt")),
            "feature_tap": "depth_head.scratch.output_conv1 input",
            "head": "conv3x3(64->32)+BN+ReLU, conv3x3(32->16)+BN+ReLU, conv1x1(16->1), bilinear to 1024",
            "output_semantics": "gamus-ndsm-agl-metric (research)",
            **params,
        },
        "evaluation": {
            "protocol": "direct metric MAE/RMSE on frozen M5 checkpoint (epoch 23)",
            "mask": "finite prediction AND finite target; negatives kept",
            "metrics": ["MAE", "RMSE", "median", "p90", "p95", "Pearson", "Spearman"],
        },
        "per_city": city_results,
        "aggregate": {
            "macro_mae": float(macro_mae),
            "macro_rmse": float(macro_rmse),
            "micro_mae": micro_mae,
            "micro_rmse": micro_rmse,
            "in_city_mae": in_city_mae,
            "cross_city_mae": cross_mae,
            "generalization_gap": gap,
        },
        "m5_reference": m5_ref,
        "software": _software(),
        "memory": "not measured",
        "wall_time_s": time.perf_counter() - t0,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    results = json.loads(json.dumps(results, allow_nan=False, default=float))

    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.json").write_text(json.dumps({
        "manifest": manifest.as_posix(),
        "base_checkpoint": str(Path(base_checkpoint).as_posix()),
        "adapt_checkpoint": str(Path(adapt_checkpoint).as_posix()),
        "output": output,
        "device": device,
        "input_size": input_size,
        "seed": seed,
        "splits": splits,
        "target_mu": target_mu,
        "target_sigma": target_sigma,
        "target_mode": "zscore" if target_mu is not None else "raw",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "README.md").write_text(
        f"# M6 Geographic Validation\n\n"
        f"Frozen adapted DA-V2-Small evaluated on {len(cities)} cities.\n"
        f"- Target mode: {'zscore (train-only mu/sigma)' if target_mu is not None else 'raw'}\n"
        f"- Cities: {', '.join(cities)}\n"
        f"- Macro MAE: {macro_mae:.4f} m\n"
        f"- Micro MAE: {micro_mae:.4f} m\n"
        f"- In-city (DC) MAE: {in_city_mae:.4f} m\n"
        f"- Cross-city MAE: {cross_mae:.4f} m\n"
        f"- Generalization gap: {gap:+.4f} m\n\n"
        f"See `config.json`, `results.json`.\n",
        encoding="utf-8",
    )

    if make_visuals:
        _visuals(out_dir, model, cities)

    print(f"M6 done: macro_mae={macro_mae:.4f} micro_mae={micro_mae:.4f} gap={gap} -> {out_dir}")
    return results


def _visuals(out_dir: Path, model: Any, cities: list[str]) -> None:
    import numpy as np  # type: ignore
    try:
        import matplotlib  # type: ignore
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as e:
        print(f"Visuals skipped ({e})")
        return

    from depthwizard.data.adapter import GamusAdapter
    from depthwizard.data.config import GamusConfig
    from depthwizard.data.manifest import load_manifest
    from depthwizard.data.schemas import GamusRecord, canonical_split

    cfg = GamusConfig(root=Path("data/gamus"))
    adapter = GamusAdapter(config=GamusConfig(root=cfg.resolve_root()))
    manifest = Path("manifests/gamus.m6.geographic.json")
    recs = [GamusRecord.from_dict(d) for d in load_manifest(manifest).get("records", [])]

    dest = Path("outputs") / "m6-geographic"
    dest.mkdir(parents=True, exist_ok=True)

    for city in cities:
        city_recs = [r for r in recs if r.sample_id.split('_')[0] == city]
        for s in city_recs[:2]:  # 2 per city
            sample = adapter.to_sample(s, load_arrays=True)
            rgb = np.asarray(sample.image)
            tgt = np.asarray(sample.height, float)
            pred = model.predict_height(rgb)
            err = np.abs(pred - tgt)

            fig, ax = plt.subplots(1, 4, figsize=(16, 4))
            ax[0].imshow(rgb)
            ax[0].set_title(f"RGB {s.sample_id}")
            ax[1].imshow(tgt, cmap="viridis", vmin=0, vmax=45)
            ax[1].set_title("GAMUS nDSM (m)")
            ax[2].imshow(pred, cmap="viridis", vmin=0, vmax=45)
            ax[2].set_title("M5 adapted (m)")
            ax[3].imshow(err, cmap="magma")
            ax[3].set_title(f"|err| MAE={np.nanmean(err):.2f}")
            for a in ax:
                a.axis("off")
            fig.suptitle(f"{city} - {s.sample_id} (diagnostic)")
            fig.tight_layout()
            fig.savefig(dest / f"{city}_{s.sample_id}.png", dpi=80)
            plt.close(fig)
    print(f"Visuals -> {dest}")


def main() -> None:
    ap = argparse.ArgumentParser(description="M6 Geographic Validation of frozen M5 adapted model")
    ap.add_argument("--manifest", required=True, help="Geographic manifest JSON")
    ap.add_argument("--base-checkpoint", required=True, help="Base DA-V2 checkpoint (e.g., checkpoints/depth_anything_v2_vits.pth)")
    ap.add_argument("--adapt-checkpoint", required=True, help="M5 adaptation head checkpoint (.pt)")
    ap.add_argument("--output", required=True, help="Output directory")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--input-size", type=int, default=518)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--splits", nargs="*", default=["val", "test"])
    ap.add_argument("--visuals", action="store_true")
    ap.add_argument("--target-mu", type=float, default=None, help="Train-only z-score mu (optional; M10)")
    ap.add_argument("--target-sigma", type=float, default=None, help="Train-only z-score sigma (optional; M10)")
    args = ap.parse_args()

    run_geographic_validation(
        manifest=args.manifest,
        base_checkpoint=args.base_checkpoint,
        adapt_checkpoint=args.adapt_checkpoint,
        output=args.output,
        device=args.device,
        input_size=args.input_size,
        seed=args.seed,
        splits=args.splits,
        make_visuals=args.visuals,
        target_mu=args.target_mu,
        target_sigma=args.target_sigma,
    )


if __name__ == "__main__":
    main()