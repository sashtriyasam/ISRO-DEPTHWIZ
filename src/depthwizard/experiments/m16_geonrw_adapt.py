"""
M16 controlled GeoNRW adaptation probe: frozen DA-V2-Small backbone + trainable
head, initialized from the M10 head, adapted on GeoNRW train-side cities (research).

Scientific question: can a small amount of controlled GeoNRW head adaptation
recover external structural correlation without touching held-out test cities?

Frozen design (pre-registered; see docs/research/m16-geonrw-adaptation.md):
- Adaptation-train: bochum, coesfeld, gelsenkirchen, guetersloh (first 6 sorted
  stems each = 24 triplets — matches the M10 24-tile budget).
- Adaptation-val: herford, paderborn (first 6 sorted stems each = 12 triplets),
  city-disjoint from train. Checkpoint selection: MAX pooled direct Pearson
  (affine-invariant, i.e. the M15 structural signal) on this val set.
- Held-out: duesseldorf/herne/neuss (absent locally; never touched) + all
  remaining triplets reserved as development-probe pool (evaluated once,
  post-selection, labeled probe — never used for selection).
- Target: FROZEN M10 GAMUS z-score stats (mu=8.037330237035235,
  sigma=10.304011604437477) passed explicitly — preserves the M10 head's
  output semantics at init; single-factor discipline (only data changes).
- Loss: plain masked L1 (NOT the rejected 2x weighting).
- Optimizer: Adam lr=1e-3 wd=0, batch 1, seed 0, 30 epochs, no augmentation.
- Init: M10 best.pt head_state (epoch 22) into a fresh seed-0 head.

Reproducible command:

    PYTHONPATH=src:<pinned-DA-V2-clone> python -m depthwizard.experiments.m16_geonrw_adapt \\
        --triplets D:/geonrw_data/triplets \\
        --m10-checkpoint experiments/dav2-gamus-head-m10-m9-targetnorm-e01/checkpoints/best.pt \\
        --output experiments/m16-geonrw-adapt-e01
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any, Optional

from depthwizard.adapt.loss import TargetScale
from depthwizard.adapt.model import AdaptedDepthModel
from depthwizard.adapt.train import set_deterministic, train_adapted_model
from depthwizard.depth.depth_anything_v2 import DepthAnythingV2Backend
from depthwizard.experiments.m15_geonrw_eval import (
    M10_MU,
    M10_SIGMA,
    enumerate_triplets,
    evaluate_triplet,
    load_triplet,
)

# Pre-registered M16 split (deterministic; fixed before any training).
TRAIN_CITIES = ["bochum", "coesfeld", "gelsenkirchen", "guetersloh"]
VAL_CITIES = ["herford", "paderborn"]
HELD_OUT_CITIES = ["duesseldorf", "herne", "neuss"]
N_PER_CITY = 6
OUT_HW = (1000, 1000)


def _software() -> dict[str, str]:
    def _v(mod: str) -> str:
        try:
            m = __import__(mod)
            return getattr(m, "__version__", "installed")
        except Exception:
            return "not installed"

    out = {"python": sys.version.split()[0], "platform": platform.platform()}
    for mod in ("torch", "numpy", "rasterio"):
        out[mod] = _v(mod)
    return out


def select_split(
    items: list[dict[str, Any]],
    train_cities: Optional[list[str]] = None,
    val_cities: Optional[list[str]] = None,
    n_per_city: int = N_PER_CITY,
    held_out: Optional[list[str]] = None,
) -> dict[str, list[dict[str, Any]]]:
    """Deterministic train/val split over triplet items.

    First-``n_per_city`` sorted stems per city. Raises on any held-out-city
    presence, any train/val overlap, or short cities. No randomness.
    """
    train_cities = train_cities or TRAIN_CITIES
    val_cities = val_cities or VAL_CITIES
    held_out = held_out or HELD_OUT_CITIES
    by_city: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        by_city.setdefault(it["city"], []).append(it)
    present_held = [c for c in held_out if c in by_city]
    if present_held:
        raise ValueError(f"Held-out cities present in adaptation pool: {present_held} — refusing to proceed")
    if set(train_cities) & set(val_cities):
        raise ValueError("Train/val cities overlap — split design violated")
    split: dict[str, list[dict[str, Any]]] = {"train": [], "val": []}
    for key, cities in (("train", train_cities), ("val", val_cities)):
        for city in cities:
            triplets = sorted(by_city.get(city, []), key=lambda t: t["stem"])
            if len(triplets) < n_per_city:
                raise ValueError(f"City {city}: only {len(triplets)} triplets, need {n_per_city}")
            split[key].extend(triplets[:n_per_city])
    tids = [t["city"] + "/" + t["stem"] for t in split["train"]]
    vids = [t["city"] + "/" + t["stem"] for t in split["val"]]
    if set(tids) & set(vids):
        raise ValueError("Train/val triplet overlap — leakage guard tripped")
    return split


def _to_samples(triplets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import numpy as np  # type: ignore

    out = []
    for t in triplets:
        s = load_triplet(t["rgb"], t["dem"])
        out.append({
            "sample_id": f"{t['city']}/{t['stem']}",
            "city": t["city"],
            "image": np.asarray(s["image"]),
            "height": np.asarray(s["height"], dtype=np.float32),
        })
    return out


def run_geonrw_adaptation(
    triplets: Path | str,
    m10_checkpoint: Path | str,
    output: Path | str,
    base_checkpoint: Optional[Path | str] = None,
    epochs: int = 30,
    lr: float = 1e-3,
    weight_decay: float = 0.0,
    seed: int = 0,
    device: str = "cpu",
    input_size: int = 518,
) -> dict[str, Any]:
    import numpy as np  # type: ignore
    import torch

    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    set_deterministic(seed)
    t0 = time.perf_counter()

    items = enumerate_triplets(triplets)
    if not items:
        raise ValueError(f"No complete (rgb, dem) triplets under {triplets}")
    split = select_split(items)
    train, val = _to_samples(split["train"]), _to_samples(split["val"])
    manifest_str = "\n".join(
        [f"train {t['city']}/{t['stem']}" for t in split["train"]]
        + [f"val {t['city']}/{t['stem']}" for t in split["val"]]
    )
    manifest_sha = hashlib.sha256(manifest_str.encode()).hexdigest()[:16]

    backend = DepthAnythingV2Backend(checkpoint=base_checkpoint, device=device, input_size=input_size, seed=seed)
    backend.load()
    model = AdaptedDepthModel.from_backend(backend, input_size=input_size, seed=seed)
    params = model.parameter_report()
    # Initialize the adaptation head FROM the frozen M10 head (domain adaptation,
    # not fresh training). Provenance recorded below; M10 checkpoint never written.
    m10_payload = torch.load(str(m10_checkpoint), map_location="cpu", weights_only=False)
    model.head.load_state_dict(m10_payload["head_state"])
    m10_extra = m10_payload.get("extra", {})
    model.target_scale = TargetScale(mode="zscore", mu=M10_MU, sigma=M10_SIGMA)
    model.assert_frozen()

    # Frozen M10 z-score stats passed explicitly: no auto-compute, no GeoNRW
    # statistics, no M7 values. Plain masked L1 (height_weight=None).
    target_scale = TargetScale(mode="zscore", mu=M10_MU, sigma=M10_SIGMA)
    summary = train_adapted_model(
        model, train, val, Path(output), epochs=epochs, lr=lr,
        weight_decay=weight_decay, seed=seed,
        selection_metric="pearson", selection_mode="max",
        out_hw=OUT_HW, target_scale=target_scale,
    )
    model.target_scale = TargetScale(mode="zscore", mu=M10_MU, sigma=M10_SIGMA)

    # Post-selection validation report (M15 affine protocol on the val cities).
    val_report = []
    for s, t in zip(val, split["val"]):
        pred = model.predict_height(s["image"], out_hw=OUT_HW)
        ev = evaluate_triplet(pred, np.asarray(s["height"], dtype=np.float64))
        ev["sample_id"] = s["sample_id"]
        val_report.append(ev)

    results = {
        "experiment_id": "m16-geonrw-adaptation",
        "kind": "controlled GeoNRW head adaptation from frozen M10 (Pearson-selected; research only)",
        "adaptation_split": {
            "train_cities": TRAIN_CITIES,
            "val_cities": VAL_CITIES,
            "held_out_cities": HELD_OUT_CITIES,
            "n_per_city": N_PER_CITY,
            "train_ids": [t["city"] + "/" + t["stem"] for t in split["train"]],
            "val_ids": [t["city"] + "/" + t["stem"] for t in split["val"]],
            "manifest_sha": manifest_sha,
        },
        "initialization": {
            "source": "M10 best head (domain adaptation, not fresh training)",
            "m10_checkpoint": str(Path(m10_checkpoint).as_posix()),
            "m10_extra": m10_extra,
        },
        "target_normalization": {
            "mode": "zscore", "mu": M10_MU, "sigma": M10_SIGMA,
            "source": "frozen M10 GAMUS stats (Option A); no GeoNRW statistics fitted",
        },
        "training": {
            "loss": "plain masked L1 in z-space (finite pred AND finite target; negatives kept)",
            "optimizer": "Adam", "lr": lr, "weight_decay": weight_decay,
            "epochs": epochs, "seed": seed, "augmentation": "none",
            "selection": "MAX pooled direct Pearson on GeoNRW val (affine-invariant structural signal)",
        },
        "model": {
            "backbone": "DepthAnythingV2-Small (frozen; requires_grad False asserted)",
            "feature_tap": "depth_head.scratch.output_conv1",
            "head": "conv3x3(64->32)+BN+ReLU, conv3x3(32->16)+BN+ReLU, conv1x1(16->1), bilinear to 1000",
            "output_semantics": "geonrw-dsm-structural (research evaluation only; not calibrated elevation)",
            **params,
        },
        "validation": val_report,
        "train_summary": summary,
        "software": _software(),
        "memory": "not measured",
        "wall_time_s": time.perf_counter() - t0,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    results = json.loads(json.dumps(results, allow_nan=False, default=float))
    (out / "config.json").write_text(json.dumps({
        "experiment_id": "m16-geonrw-adaptation",
        "triplets": str(Path(triplets).as_posix()),
        "m10_checkpoint": str(Path(m10_checkpoint).as_posix()),
        "base_checkpoint": str(Path(base_checkpoint).as_posix()) if base_checkpoint else None,
        "output": str(Path(output).as_posix()),
        "train_cities": TRAIN_CITIES, "val_cities": VAL_CITIES,
        "held_out_cities": HELD_OUT_CITIES, "n_per_city": N_PER_CITY,
        "manifest_sha": manifest_sha,
        "epochs": epochs, "lr": lr, "weight_decay": weight_decay, "seed": seed,
        "device": device, "input_size": input_size,
        "target_mu": M10_MU, "target_sigma": M10_SIGMA,
        "selection_metric": "pearson", "selection_mode": "max",
        "loss": "plain masked L1",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    best_ep, best_val = summary.get("best_epoch"), summary.get("best_value")
    (out / "README.md").write_text(
        f"# M16 GeoNRW Adaptation (frozen M10 → GeoNRW head)\n\n"
        f"Pearson-selected best epoch {best_ep} (val Pearson {best_val:.4f}).\n"
        f"- Train: {len(split['train'])} triplets ({', '.join(TRAIN_CITIES)})\n"
        f"- Val: {len(split['val'])} triplets ({', '.join(VAL_CITIES)})\n"
        f"- Held out: {', '.join(HELD_OUT_CITIES)} (absent) + reserve pool (probe only)\n"
        f"- Manifest SHA: {manifest_sha}\n\n"
        f"Development probe only — NOT a formal held-out test. See `results.json`.\n",
        encoding="utf-8",
    )
    print(f"M16 done: best_epoch={best_ep} val_pearson={best_val:.4f} -> {out}")
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description="M16 controlled GeoNRW adaptation from frozen M10")
    ap.add_argument("--triplets", required=True)
    ap.add_argument("--m10-checkpoint", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--base-checkpoint", default=None)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--input-size", type=int, default=518)
    args = ap.parse_args()
    run_geonrw_adaptation(
        triplets=args.triplets, m10_checkpoint=args.m10_checkpoint,
        output=args.output, base_checkpoint=args.base_checkpoint,
        epochs=args.epochs, lr=args.lr, weight_decay=args.weight_decay,
        seed=args.seed, device=args.device, input_size=args.input_size,
    )


if __name__ == "__main__":
    main()
