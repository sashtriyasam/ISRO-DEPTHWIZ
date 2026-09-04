"""
Frozen GAMUS baseline experiment: Depth Anything V2 Small (M3).

Pipeline (inference only — no training, no calibration, no DSM):

    manifest records (deterministic)
      -> GamusAdapter raw arrays (RGB uint8 HWC input; height float32 meters target)
      -> DepthAnythingV2Backend.infer (relative depth, source-sized)
      -> depthwizard.eval (deterministic mask, per-image affine eval, metrics)
      -> compact config.json + results.json + README.md

Guardrails: backend output is relative (Rule A/B); evaluation alignment is
per-image and never leaves the results file (Rule E); raw relative-vs-meter
MAE is never computed (Rule F); 3-tile runs are labeled bring-up (Rule H).

Reproducible command:

    python -m depthwizard.experiments.depth_anything_v2 \\
        --manifest manifests/gamus.manifest.json --split train \\
        --device cpu --output experiments/depth-anything-v2/bringup-cpu-3tile
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

from depthwizard.data.adapter import GamusAdapter
from depthwizard.data.config import GamusConfig
from depthwizard.data.manifest import load_manifest
from depthwizard.data.schemas import GamusRecord, canonical_split
from depthwizard.depth.depth_anything_v2 import DepthAnythingV2Backend
from depthwizard.eval.alignment import evaluate_sample


def _software_versions() -> dict[str, str]:
    def _v(mod: str) -> str:
        try:
            m = __import__(mod)
            return getattr(m, "__version__", "installed")
        except Exception:
            return "not installed"

    versions = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch": _v("torch"),
        "torchvision": _v("torchvision"),
        "numpy": _v("numpy"),
        "h5py": _v("h5py"),
        "cv2": _v("cv2"),
        "PIL": _v("PIL"),
    }
    try:
        import torch  # type: ignore

        versions["cuda_available"] = str(torch.cuda.is_available())
    except Exception:
        versions["cuda_available"] = "unknown"
    return versions


def _load_config_file(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def select_records(
    manifest_path: Path,
    split: str,
    sample_ids: Optional[list[str]] = None,
    subset_path: Optional[Path] = None,
    max_samples: Optional[int] = None,
) -> list[GamusRecord]:
    """Deterministic record selection: manifest order, optional ID/subset filter."""
    from depthwizard.data.schemas import GAMUS_SPLITS

    data = load_manifest(manifest_path)
    recs = [GamusRecord.from_dict(d) for d in data.get("records", [])]
    recs = [r for r in recs if r.split == canonical_split(split)]
    if subset_path is not None:
        sub = load_manifest(subset_path)
        wanted = {GamusRecord.from_dict(d).sample_id for d in sub.get("records", [])}
        recs = [r for r in recs if r.sample_id in wanted]
    if sample_ids:
        wanted = set(sample_ids)
        recs = [r for r in recs if r.sample_id in wanted]
    order = {s: i for i, s in enumerate(GAMUS_SPLITS)}
    recs.sort(key=lambda r: (order.get(r.split, 99), r.sample_id))
    if max_samples is not None:
        recs = recs[:max_samples]
    return recs


def run_experiment(
    manifest: Path | str,
    output: Path | str,
    split: str = "train",
    sample_ids: Optional[list[str]] = None,
    subset: Optional[Path | str] = None,
    device: str = "cpu",
    input_size: int = 518,
    checkpoint: Optional[Path | str] = None,
    seed: int = 0,
    max_samples: Optional[int] = None,
    backend: Optional[DepthAnythingV2Backend] = None,
    root: Optional[Path | str] = None,
    make_visuals: bool = False,
    visual_dir: Optional[Path | str] = None,
) -> dict[str, Any]:
    """Run the frozen baseline and write compact artifacts. Returns results dict."""
    import numpy as np  # type: ignore

    manifest = Path(manifest)
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    t_exp0 = time.perf_counter()

    records = select_records(manifest, split, sample_ids, Path(subset) if subset else None, max_samples)
    if not records:
        raise ValueError("No records selected — check manifest/split/sample filter")

    cfg = GamusConfig(root=Path(root) if root else Path("data/gamus"))
    adapter_root = cfg.resolve_root()
    adapter = GamusAdapter(config=GamusConfig(root=adapter_root))

    be = backend or DepthAnythingV2Backend(checkpoint=checkpoint, device=device, input_size=input_size, seed=seed)
    t_load0 = time.perf_counter()
    be.load()
    load_s = time.perf_counter() - t_load0

    per_sample: list[dict[str, Any]] = []
    for rec in records:
        sample = adapter.to_sample(rec, load_arrays=True)
        if sample.image is None:
            raise FileNotFoundError(f"Missing RGB for '{rec.sample_id}' (root {adapter_root})")
        if sample.height is None:
            raise FileNotFoundError(f"Missing height for '{rec.sample_id}' (root {adapter_root})")
        result = be.infer(np.asarray(sample.image))
        ev = evaluate_sample(np.asarray(result.prediction, dtype=np.float64), np.asarray(sample.height, dtype=np.float64))
        per_sample.append(
            {
                "sample_id": rec.sample_id,
                "split": rec.split,
                "pred_shape": list(result.shape),
                "pred_min": result.to_dict()["pred_min"],
                "pred_max": result.to_dict()["pred_max"],
                "pred_mean": result.to_dict()["pred_mean"],
                "pred_std": result.to_dict()["pred_std"],
                "finite_coverage": result.finite_coverage,
                "valid_coverage": ev["valid_coverage"],
                "n_valid": ev["n_valid"],
                "affine_a": ev["affine"]["a"],
                "affine_b": ev["affine"]["b"],
                "affine_degenerate": ev["affine"]["degenerate"],
                "aligned_mae": ev["aligned"].get("mae"),
                "aligned_rmse": ev["aligned"].get("rmse"),
                "pearson": ev["pearson"],
                "spearman": ev["spearman"],
                "inference_time_s": result.inference_time_s,
            }
        )

    def _mean(key: str) -> Optional[float]:
        vals = [s[key] for s in per_sample if s[key] is not None]
        return float(sum(vals) / len(vals)) if vals else None

    total_inf = sum(s["inference_time_s"] or 0.0 for s in per_sample)
    results: dict[str, Any] = {
        "experiment_kind": "frozen-baseline (inference only; NOT calibrated height)",
        "bring_up": len(per_sample) <= 3,
        "bring_up_note": "Bring-up / smoke evaluation only — not the final benchmark."
        if len(per_sample) <= 3
        else None,
        "dataset": {
            "source": "earthflow/GAMUS",
            "manifest": manifest.as_posix(),
            "split": canonical_split(split),
            "sample_ids": [r.sample_id for r in records],
            "subset": Path(subset).as_posix() if subset else None,
            "target_semantics": "nDSM/AGL ground truth (meters; NOT DSM/elevation)",
        },
        "model": be.config_dict() if hasattr(be, "config_dict") else {"backend": be.name},
        "evaluation": {
            "protocol": "per-image-affine-eval-v1 (evaluation only, not calibration)",
            "mask": "finite prediction AND finite target; negatives kept (M2 sentinel-candidate rule)",
            "metrics_note": "MAE/RMSE are post-alignment only; raw relative-vs-meter MAE never computed (Rule F)",
        },
        "n_samples": len(per_sample),
        "per_sample": per_sample,
        "aggregate": {
            "aligned_mae_mean": _mean("aligned_mae"),
            "aligned_rmse_mean": _mean("aligned_rmse"),
            "pearson_mean": _mean("pearson"),
            "spearman_mean": _mean("spearman"),
            "valid_coverage_mean": _mean("valid_coverage"),
            "inference_time_s_mean": (total_inf / len(per_sample)) if per_sample else None,
            "inference_time_s_total": total_inf,
            "model_load_s": load_s,
            "wall_time_s": time.perf_counter() - t_exp0,
        },
        "software": _software_versions(),
        "memory": "not measured",
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    (out_dir / "config.json").write_text(json.dumps(_config_snapshot(be, manifest, split, sample_ids, subset, device, input_size, checkpoint, seed, max_samples, root), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readme = (
        f"# Frozen DA-V2-Small baseline — {out_dir.name}\n\n"
        f"- Samples ({len(per_sample)}, split {canonical_split(split)}): "
        + ", ".join(f"`{r.sample_id}`" for r in records)
        + "\n- Target: GAMUS nDSM/AGL ground truth (meters). Prediction: relative depth (NOT meters).\n"
        "- Metrics are post-per-image-affine-alignment research numbers, not calibrated height performance.\n"
        + ("- **Bring-up / smoke evaluation only — not the final benchmark.**\n" if len(per_sample) <= 3 else "")
        + "\nSee `config.json` (exact reproduction inputs) and `results.json` (compact measurements).\n"
    )
    (out_dir / "README.md").write_text(readme, encoding="utf-8")

    if make_visuals:
        _write_visuals(per_sample, records, adapter, be, visual_dir or (Path("outputs") / out_dir.name))

    print(f"Experiment done: n={len(per_sample)} "
          f"aligned_mae_mean={results['aggregate']['aligned_mae_mean']} "
          f"pearson_mean={results['aggregate']['pearson_mean']} "
          f"-> {out_dir}")
    return results


def _config_snapshot(be: Any, manifest: Path, split: str, sample_ids: Optional[list[str]], subset: Any, device: str, input_size: int, checkpoint: Any, seed: int, max_samples: Any, root: Any) -> dict[str, Any]:
    return {
        "manifest": manifest.as_posix(),
        "split": canonical_split(split),
        "sample_ids": sample_ids,
        "subset": Path(subset).as_posix() if subset else None,
        "device": device,
        "input_size": input_size,
        "checkpoint": Path(checkpoint).as_posix() if checkpoint else None,
        "seed": seed,
        "max_samples": max_samples,
        "root": Path(root).as_posix() if root else None,
        "backend": be.config_dict() if hasattr(be, "config_dict") else {"backend": getattr(be, "name", "unknown")},
    }


def _write_visuals(per_sample: list[dict], records: list[GamusRecord], adapter: GamusAdapter, be: Any, visual_dir: Path | str) -> None:
    """Diagnostic RGB/depth/target/aligned/error panels (git-ignored location)."""
    import numpy as np  # type: ignore

    try:
        import matplotlib  # type: ignore

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # type: ignore
    except Exception as e:
        print(f"Visuals skipped (matplotlib unavailable: {e})")
        return
    from depthwizard.eval.alignment import apply_affine

    out = Path(visual_dir)
    out.mkdir(parents=True, exist_ok=True)
    by_id = {s["sample_id"]: s for s in per_sample}
    for rec in records:
        sample = adapter.to_sample(rec, load_arrays=True)
        rgb = np.asarray(sample.image)
        tgt = np.asarray(sample.height, dtype=np.float64)
        res = be.infer(rgb)
        pred = np.asarray(res.prediction, dtype=np.float64)
        s = by_id[rec.sample_id]
        aligned = apply_affine(pred, s["affine_a"], s["affine_b"]) if not s["affine_degenerate"] else np.full_like(pred, np.nan)
        err = np.abs(aligned - tgt)
        fig, axes = plt.subplots(1, 5, figsize=(20, 4))
        axes[0].imshow(rgb)
        axes[0].set_title(f"RGB {rec.sample_id}")
        axes[1].imshow(pred, cmap="inferno")
        axes[1].set_title("relative depth")
        axes[2].imshow(tgt, cmap="viridis")
        axes[2].set_title("GAMUS nDSM (m)")
        axes[3].imshow(aligned, cmap="viridis")
        axes[3].set_title(f"aligned a={s['affine_a']:.3f} b={s['affine_b']:.3f}" if s["affine_a"] is not None else "aligned n/a")
        im = axes[4].imshow(err, cmap="magma")
        axes[4].set_title(f"|err| MAE={s['aligned_mae']:.3f}" if s["aligned_mae"] is not None else "|err| n/a")
        for ax in axes:
            ax.axis("off")
        fig.colorbar(im, ax=axes[4], fraction=0.046)
        fig.suptitle(f"{rec.sample_id} — diagnostic only (relative output; aligned research view)")
        fig.tight_layout()
        fig.savefig(out / f"{rec.sample_id}.png", dpi=80)
        plt.close(fig)
    print(f"Visuals -> {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Frozen Depth Anything V2 Small baseline on GAMUS")
    ap.add_argument("--manifest", type=str, required=True)
    ap.add_argument("--split", type=str, default="train")
    ap.add_argument("--samples", type=str, nargs="*", default=None)
    ap.add_argument("--subset", type=str, default=None)
    ap.add_argument("--device", type=str, default="cpu")
    ap.add_argument("--input-size", type=int, default=518)
    ap.add_argument("--checkpoint", type=str, default=None)
    ap.add_argument("--output", type=str, required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-samples", type=int, default=None)
    ap.add_argument("--root", type=str, default=None)
    ap.add_argument("--config", type=str, default=None, help="JSON config file (CLI flags override)")
    ap.add_argument("--visuals", action="store_true")
    ap.add_argument("--visual-dir", type=str, default=None)
    args = ap.parse_args()
    file_cfg: dict[str, Any] = _load_config_file(args.config) if args.config else {}
    manifest = args.manifest or file_cfg.get("manifest")
    run_experiment(
        manifest=manifest,
        output=args.output,
        split=args.split if args.split else file_cfg.get("split", "train"),
        sample_ids=args.samples or file_cfg.get("sample_ids"),
        subset=args.subset or file_cfg.get("subset"),
        device=args.device or file_cfg.get("device", "cpu"),
        input_size=args.input_size or file_cfg.get("input_size", 518),
        checkpoint=args.checkpoint or file_cfg.get("checkpoint"),
        seed=args.seed if args.seed is not None else file_cfg.get("seed", 0),
        max_samples=args.max_samples or file_cfg.get("max_samples"),
        root=args.root or file_cfg.get("root"),
        make_visuals=args.visuals or bool(file_cfg.get("visuals", False)),
        visual_dir=args.visual_dir or file_cfg.get("visual_dir"),
    )


if __name__ == "__main__":
    main()
