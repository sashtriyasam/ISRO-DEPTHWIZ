"""
M15 GeoNRW external evaluation of the frozen M10 candidate (research only).

Method selected (see docs/research/m15-geonrw-external-eval.md, "Why this
method was selected"): the semantics gate established the GeoNRW target as
ABSOLUTE DSM (first-return LiDAR surface elevation, meters) — NOT nDSM/AGL —
with no DTM available, so direct MAE scoring is scientifically invalid.
The defensible comparison is the established per-image affine research
protocol (M3/M6): it measures whether M10's learned height STRUCTURE
transfers to real DSM, without claiming metric-nDSM performance.

Pipeline (frozen M10, one-shot, no training, no tuning):
    GeoNRW triplet (RGB JP2 + DEM tif + seg, 1000x1000 @1m, EPSG:25832)
      -> RGB first-3-channels uint8 HWC + DEM float32 (nodata -9999 -> NaN)
      -> M10 predict_height(rgb, out_hw=(1000,1000))  [exact grid, no resampling]
      -> per-image affine fit (target ~= a*pred + b) + Pearson/Spearman
      -> per-city + macro/micro aggregates, meters

Reproducible command:

    PYTHONPATH=src:<pinned-DA-V2-clone> python -m depthwizard.experiments.m15_geonrw_eval \\
        --triplets D:/geonrw_data/triplets \\
        --adapt-checkpoint experiments/dav2-gamus-head-m10-m9-targetnorm-e01/checkpoints/best.pt \\
        --output experiments/m15-geonrw-eval

Requires the optional `rasterio` package (test-only dependency, same pattern
as matplotlib visuals elsewhere). No shared interfaces are modified.
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

M10_MU = 8.037330237035235
M10_SIGMA = 10.304011604437477
M10_BEST_EPOCH = 22
M10_VAL_MAE = 5.8204


def _require_rasterio() -> Any:
    try:
        import rasterio  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "rasterio is required for M15 GeoNRW evaluation (pip install rasterio)"
        ) from e
    return rasterio


def parse_triplet_stem(filename: str) -> Optional[tuple[str, str]]:
    """Split a GeoNRW filename into (stem, kind).

    E.g. ``368_5702_rgb.jp2`` -> (``368_5702``, ``rgb``);
    ``368_5702_dem.tif`` -> (``368_5702``, ``dem``).
    Returns None for unrecognized names (never silently misgrouped).
    """
    base = Path(filename).name
    if base.endswith("_rgb.jp2"):
        return base[: -len("_rgb.jp2")], "rgb"
    if base.endswith("_dem.tif"):
        return base[: -len("_dem.tif")], "dem"
    if base.endswith("_seg.tif"):
        return base[: -len("_seg.tif")], "seg"
    return None


def enumerate_triplets(root: Path | str) -> list[dict[str, Any]]:
    """Enumerate complete (rgb, dem) pairs under <root>/<city>/*, sorted.

    Segmentation files are NOT required for the height evaluation.
    Deterministic sorted order; no randomness, no selection.
    """
    root = Path(root)
    groups: dict[tuple[str, str], dict[str, Path]] = {}
    for city_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        for f in sorted(city_dir.iterdir()):
            if not f.is_file():
                continue
            parsed = parse_triplet_stem(f.name)
            if parsed is None:
                continue
            stem, kind = parsed
            if kind in ("rgb", "dem"):
                groups.setdefault((city_dir.name, stem), {})[kind] = f
    out = [
        {"city": city, "stem": stem, "rgb": str(g["rgb"]), "dem": str(g["dem"])}
        for (city, stem), g in sorted(groups.items())
        if set(g) == {"rgb", "dem"}
    ]
    return out


def shares_horizontal_frame(rgb_crs_str: str, dem_crs_str: str) -> bool:
    """Check whether a DEM CRS string shares the RGB CRS's horizontal frame.

    GeoNRW DEMs carry a compound-like WKT (UTM 32N + DHHN92 height) while the
    RGB JP2 carries plain EPSG:25832. The shared horizontal frame is verified
    by substring match of the RGB CRS name inside the DEM WKT. Requires the
    optional `pyproj` package; without it, only exact CRS equality passes.
    """
    if rgb_crs_str == dem_crs_str:
        return True
    try:
        import pyproj  # type: ignore
    except Exception:
        return False
    try:
        name = pyproj.CRS(rgb_crs_str).name
    except Exception:
        return False
    return bool(name) and name in dem_crs_str


def load_triplet(rgb_path: str | Path, dem_path: str | Path) -> dict[str, Any]:
    """Load one RGB/DEM pair into model-ready arrays + geo metadata.

    - RGB: first 3 channels as uint8 HWC (GeoNRW JP2 stores RGBI).
    - DEM: float32 meters; nodata (-9999 or file tag) -> NaN.
    - Grids must match exactly (same W/H/transform/bounds); horizontal CRS
      frames must match (a vertical-datum-only difference, e.g. DHHN92 on the
      DEM side, is accepted and recorded, never silently resampled).
    """
    rasterio = _require_rasterio()
    import numpy as np  # type: ignore

    with rasterio.open(rgb_path) as rgb_ds, rasterio.open(dem_path) as dem_ds:
        if (rgb_ds.width, rgb_ds.height) != (dem_ds.width, dem_ds.height):
            raise ValueError(
                f"Grid mismatch RGB {(rgb_ds.width, rgb_ds.height)} vs "
                f"DEM {(dem_ds.width, dem_ds.height)}: refusing to resample silently"
            )
        if tuple(rgb_ds.transform) != tuple(dem_ds.transform):
            raise ValueError("RGB/DEM affine transforms differ: refusing to resample silently")
        rgb_crs_str, dem_crs_str = str(rgb_ds.crs), str(dem_ds.crs)
        if rgb_crs_str == dem_crs_str:
            crs_note = "identical CRS"
        elif shares_horizontal_frame(rgb_crs_str, dem_crs_str):
            crs_note = ("shared horizontal frame; DEM carries extra vertical-datum "
                        "metadata (e.g. DHHN92) — recorded, not resampled")
        else:
            raise ValueError(f"CRS mismatch RGB {rgb_ds.crs} vs DEM {dem_ds.crs}")
        rgb = rgb_ds.read()  # (C, H, W)
        dem = dem_ds.read(1).astype(np.float64)
        nodata = dem_ds.nodata
        geo = {
            "crs": str(rgb_ds.crs),
            "dem_crs": str(dem_ds.crs),
            "crs_note": crs_note,
            "transform": list(rgb_ds.transform),
            "res": list(rgb_ds.res),
            "bounds": list(rgb_ds.bounds),
            "width": rgb_ds.width,
            "height": rgb_ds.height,
            "rgb_count": rgb_ds.count,
            "rgb_dtype": str(rgb_ds.dtypes[0]),
            "dem_dtype": str(dem_ds.dtypes[0]),
            "dem_nodata_tag": nodata,
        }
    if rgb.shape[0] < 3:
        raise ValueError(f"RGB needs >=3 channels, got shape {rgb.shape}")
    image = np.ascontiguousarray(rgb[:3].transpose(1, 2, 0)).astype(np.uint8)
    height = np.asarray(dem, dtype=np.float64)
    if nodata is not None and np.isfinite(nodata):
        height = np.where(height == float(nodata), np.nan, height)
    return {"image": image, "height": height, "geo": geo}


def _pearson_spearman(p: Any, t: Any) -> tuple[Optional[float], Optional[float]]:
    import numpy as np  # type: ignore

    if p.size < 3 or float(p.var()) == 0.0 or float(t.var()) == 0.0:
        return None, None
    pearson = float(np.corrcoef(p, t)[0, 1])
    from scipy.stats import spearmanr as _sr  # noqa: PLC0415  (optional; None if absent)

    try:
        spearman = float(_sr(p, t).statistic)
    except Exception:
        # Rank correlation via argsort fallback (no scipy dependency).
        pr = np.argsort(np.argsort(p)).astype(float)
        tr = np.argsort(np.argsort(t)).astype(float)
        spearman = float(np.corrcoef(pr, tr)[0, 1]) if pr.var() and tr.var() else None
    return pearson, spearman


def evaluate_triplet(pred: Any, target: Any) -> dict[str, Any]:
    """Per-image affine research eval (M3/M6 protocol) + diagnostic direct MAE.

    The diagnostic direct MAE is reported ONLY to show the datum-offset
    dominance; it must never be read as nDSM performance.
    """
    import numpy as np  # type: ignore

    from depthwizard.eval.alignment import affine_fit

    p = np.asarray(pred, dtype=np.float64)
    t = np.asarray(target, dtype=np.float64)
    if p.shape != t.shape:
        raise ValueError(f"Prediction shape {p.shape} != target shape {t.shape}")
    mask = np.isfinite(p) & np.isfinite(t)
    n = int(mask.sum())
    if n == 0:
        raise ValueError("evaluate_triplet: zero valid pixels")
    pv, tv = p[mask], t[mask]
    a, b, degenerate = affine_fit(p, t, mask)
    if degenerate or a is None or b is None:
        aligned_mae: Optional[float] = None
        aligned_rmse: Optional[float] = None
    else:
        d = (a * pv + b) - tv
        aligned_mae = float(np.abs(d).mean())
        aligned_rmse = float(np.sqrt((d ** 2).mean()))
    pearson, spearman = _pearson_spearman(pv, tv)
    return {
        "n_valid": n,
        "valid_fraction": float(n / p.size),
        "target_min": float(tv.min()),
        "target_max": float(tv.max()),
        "target_mean": float(tv.mean()),
        "pred_min": float(pv.min()),
        "pred_max": float(pv.max()),
        "pred_mean": float(pv.mean()),
        "affine_a": a,
        "affine_b": b,
        "degenerate": bool(degenerate),
        "aligned_mae": aligned_mae,
        "aligned_rmse": aligned_rmse,
        "pearson": pearson,
        "spearman": spearman,
        "direct_mae_diagnostic": float(np.abs(pv - tv).mean()),
    }


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


def run_geonrw_eval(
    triplets: Path | str,
    adapt_checkpoint: Path | str,
    output: Path | str,
    base_checkpoint: Optional[Path | str] = None,
    device: str = "cpu",
    input_size: int = 518,
    seed: int = 0,
) -> dict[str, Any]:
    import torch

    from depthwizard.adapt.loss import TargetScale
    from depthwizard.adapt.model import AdaptedDepthModel
    from depthwizard.depth.depth_anything_v2 import DepthAnythingV2Backend

    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    items = enumerate_triplets(triplets)
    if not items:
        raise ValueError(f"No complete (rgb, dem) triplets under {triplets}")
    digest = hashlib.sha256("\n".join(f"{i['city']}/{i['stem']}" for i in items).encode()).hexdigest()[:16]
    print(f"M15 frozen eval on {len(items)} triplets (set sha {digest})")

    backend = DepthAnythingV2Backend(checkpoint=base_checkpoint, device=device, input_size=input_size, seed=seed)
    backend.load()
    model = AdaptedDepthModel.from_backend(backend, input_size=input_size, seed=seed)
    payload = torch.load(str(adapt_checkpoint), map_location="cpu", weights_only=False)
    model.head.load_state_dict(payload["head_state"])
    model.target_scale = TargetScale(mode="zscore", mu=M10_MU, sigma=M10_SIGMA)
    model.assert_frozen()
    ckpt_extra = payload.get("extra", {})
    ckpt_bytes = Path(adapt_checkpoint).stat().st_size

    per_city: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        sample = load_triplet(it["rgb"], it["dem"])
        h, w = sample["height"].shape
        pred = model.predict_height(sample["image"], out_hw=(h, w))
        ev = evaluate_triplet(pred, sample["height"])
        ev.update({"city": it["city"], "stem": it["stem"], "geo": sample["geo"]})
        per_city.setdefault(it["city"], []).append(ev)
        print(f"  {it['city']}/{it['stem']}: aligned_mae={ev['aligned_mae'] and round(ev['aligned_mae'], 3)} "
              f"pearson={ev['pearson'] and round(ev['pearson'], 3)}")

    def _mean(vals: list) -> Optional[float]:
        v = [x for x in vals if x is not None]
        return float(sum(v) / len(v)) if v else None

    city_results = {}
    for city in sorted(per_city):
        evs = per_city[city]
        n_px = sum(e["n_valid"] for e in evs)
        city_results[city] = {
            "n_triplets": len(evs),
            "n_valid_pixels": n_px,
            "aligned_mae_macro": _mean([e["aligned_mae"] for e in evs]),
            "aligned_rmse_macro": _mean([e["aligned_rmse"] for e in evs]),
            "pearson_macro": _mean([e["pearson"] for e in evs]),
            "spearman_macro": _mean([e["spearman"] for e in evs]),
            "direct_mae_diagnostic_macro": _mean([e["direct_mae_diagnostic"] for e in evs]),
            "target_mean": float(sum(e["target_mean"] * e["n_valid"] for e in evs) / max(1, n_px)),
            "target_min": min(e["target_min"] for e in evs),
            "target_max": max(e["target_max"] for e in evs),
            "per_triplet": [
                {k: e[k] for k in ("stem", "n_valid", "aligned_mae", "aligned_rmse",
                                   "pearson", "spearman", "direct_mae_diagnostic",
                                   "affine_a", "affine_b", "degenerate")}
                for e in evs
            ],
        }
    all_evs = [e for evs in per_city.values() for e in evs]
    total_px = sum(e["n_valid"] for e in all_evs)
    results = {
        "experiment_id": "m15-geonrw-external-eval",
        "kind": "frozen-M10 external transfer probe on GeoNRW (affine research protocol; no training, no tuning)",
        "frozen_model": {
            "adaptation_checkpoint": str(Path(adapt_checkpoint).as_posix()),
            "checkpoint_bytes": ckpt_bytes,
            "checkpoint_extra": ckpt_extra,
            "m10_best_epoch": M10_BEST_EPOCH,
            "m10_val_mae": M10_VAL_MAE,
            "target_mu": M10_MU,
            "target_sigma": M10_SIGMA,
            "backbone": "DepthAnythingV2-Small (frozen)",
            "input_size": input_size,
            "device": device,
        },
        "dataset": {
            "source": "torchgeo/geonrw (IEEE DataPort GeoNRW triplets)",
            "triplet_root": str(Path(triplets).as_posix()),
            "n_triplets": len(items),
            "triplet_set_sha": digest,
            "cities": sorted(per_city),
            "city_counts": {c: len(v) for c, v in sorted(per_city.items())},
            "target_semantics": "absolute DSM (first-return LiDAR surface elevation, meters) — NOT nDSM/AGL",
        },
        "protocol": {
            "note": "Per-image affine alignment (M3/M6 research protocol). Aligned metrics measure "
                    "structural transfer, NOT metric-nDSM performance. Direct MAE is diagnostic only "
                    "(datum-offset dominated). No checkpoint selection, no tuning on this data.",
            "mask": "finite prediction AND finite DEM (nodata -9999 excluded); negatives kept",
        },
        "per_city": city_results,
        "aggregate": {
            "macro_aligned_mae": _mean([c["aligned_mae_macro"] for c in city_results.values()]),
            "macro_aligned_rmse": _mean([c["aligned_rmse_macro"] for c in city_results.values()]),
            "macro_pearson": _mean([c["pearson_macro"] for c in city_results.values()]),
            "macro_spearman": _mean([c["spearman_macro"] for c in city_results.values()]),
            "macro_direct_mae_diagnostic": _mean([c["direct_mae_diagnostic_macro"] for c in city_results.values()]),
            "micro_aligned_mae": float(sum(
                (c["aligned_mae_macro"] or 0.0) * c["n_valid_pixels"] for c in city_results.values()
            ) / max(1, total_px)) if all(c["aligned_mae_macro"] is not None for c in city_results.values()) else None,
            "total_valid_pixels": total_px,
        },
        "software": _software(),
        "memory": "not measured",
        "wall_time_s": time.perf_counter() - t0,
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    results = json.loads(json.dumps(results, allow_nan=False, default=float))
    (out_dir / "config.json").write_text(json.dumps({
        "triplets": str(Path(triplets).as_posix()),
        "adapt_checkpoint": str(Path(adapt_checkpoint).as_posix()),
        "base_checkpoint": str(Path(base_checkpoint).as_posix()) if base_checkpoint else None,
        "output": str(Path(output).as_posix()),
        "device": device, "input_size": input_size, "seed": seed,
        "target_mu": M10_MU, "target_sigma": M10_SIGMA,
        "n_triplets": len(items), "triplet_set_sha": digest,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    agg = results["aggregate"]
    (out_dir / "README.md").write_text(
        f"# M15 GeoNRW External Eval (frozen M10)\n\n"
        f"Affined research protocol on {len(items)} triplets ({digest}).\n"
        f"- Macro aligned MAE: {agg['macro_aligned_mae']:.4f} m\n"
        f"- Micro aligned MAE: {agg['micro_aligned_mae']:.4f} m\n"
        f"- Macro Pearson: {agg['macro_pearson']:.4f}\n"
        f"- Direct MAE (diagnostic, datum-offset dominated): {agg['macro_direct_mae_diagnostic']:.4f} m\n\n"
        f"Structural transfer only — NOT metric-nDSM performance. See `results.json`.\n",
        encoding="utf-8",
    )
    print(f"M15 done: macro_aligned_mae={agg['macro_aligned_mae']:.4f} -> {out_dir}")
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description="M15 frozen-M10 GeoNRW external evaluation")
    ap.add_argument("--triplets", required=True)
    ap.add_argument("--adapt-checkpoint", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--base-checkpoint", default=None)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--input-size", type=int, default=518)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    run_geonrw_eval(
        triplets=args.triplets, adapt_checkpoint=args.adapt_checkpoint,
        output=args.output, base_checkpoint=args.base_checkpoint,
        device=args.device, input_size=args.input_size, seed=args.seed,
    )


if __name__ == "__main__":
    main()
