"""
Empirical H5 probe for real GAMUS samples.

Inspects actual files on disk (no downloads, no raw-data modification) and
produces a compact machine-readable report (JSON) plus a Markdown summary.
Statistics are computed by this tool — never hand-typed.

For each sample × modality the probe records: H5 key used, shape, dtype,
min/max, finite coverage, NaN/Inf counts, negative/zero counts, percentile
summary (p0/1/5/25/50/75/95/99/100), and — for class labels — unique values
with pixel frequencies. Repeated exact height values occupying >=1% of a tile
are reported as sentinel *candidates requiring interpretation* (never labeled
as nodata automatically).

Cross-modality spatial alignment (H, W) is checked per sample and reported as
`aligned: true/false` with actionable detail; the probe never resizes/crops.
"""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path
from typing import Any, Iterable, Optional

from depthwizard.data.config import GamusConfig
from depthwizard.data.manifest import discover_records
from depthwizard.data.schemas import GAMUS_VALID_LABELS, GamusRecord

# Fraction of a tile above which a repeated exact height value is flagged as
# a sentinel candidate (1% of 1024*1024 ~= 10486 pixels).
SENTINEL_FRACTION = 0.01
PERCENTILES = (0, 1, 5, 25, 50, 75, 95, 99, 100)


def _read_h5(path: Path) -> tuple[Any, str]:
    """Read the primary dataset from an H5 file. Returns (ndarray, key_used).

    Key preference mirrors the adapter: `image`, then `data`, then first
    dataset. Raises FileNotFoundError / KeyError / ValueError with actionable
    messages (never returns silently coerced data).
    """
    try:
        import h5py  # type: ignore
    except Exception as e:
        raise RuntimeError(f"h5py required to probe {path}: {e}") from e
    if not path.is_file():
        raise FileNotFoundError(f"H5 file not found: {path}")
    with h5py.File(str(path), "r") as f:
        keys = list(f.keys())
        if "image" in f:
            key = "image"
        elif "data" in f:
            key = "data"
        else:
            key = next((k for k in keys if hasattr(f[k], "shape")), None)
            if key is None:
                raise KeyError(f"No dataset found in {path}; H5 keys={keys}")
        arr = f[key][()]
    return arr, key


def _summarize_array(arr: Any) -> dict[str, Any]:
    """Finite/NaN/Inf/range summary for a numeric array (no value coercion)."""
    import numpy as np  # type: ignore

    flat = np.asarray(arr)
    total = int(flat.size)
    try:
        finite_mask = np.isfinite(flat.astype(np.float64, copy=False))
    except Exception:
        finite_mask = np.ones(total, dtype=bool)
    finite = int(finite_mask.sum())
    nan_c = int(np.isnan(flat.astype(np.float64, copy=False)).sum()) if total else 0
    inf_c = int(np.isinf(flat.astype(np.float64, copy=False)).sum()) if total else 0
    out: dict[str, Any] = {
        "count": total,
        "finite": finite,
        "finite_pct": (100.0 * finite / total) if total else 0.0,
        "nan": nan_c,
        "inf": inf_c,
    }
    if finite:
        fvals = flat[finite_mask].astype(np.float64, copy=False)
        out["min"] = float(fvals.min())
        out["max"] = float(fvals.max())
        out["percentiles"] = {f"p{p}": float(np.percentile(fvals, p)) for p in PERCENTILES}
        out["negative"] = int((fvals < 0).sum())
        out["zero"] = int((fvals == 0).sum())
    else:
        out.update({"min": None, "max": None, "percentiles": {}, "negative": 0, "zero": 0})
    return out


def _class_details(arr: Any) -> dict[str, Any]:
    """Unique values + pixel frequencies for a label array (exact stored values)."""
    import numpy as np  # type: ignore

    flat = np.asarray(arr).ravel()
    uq, ct = np.unique(flat, return_counts=True)
    order = list(np.argsort(-ct))
    values = [
        {"value": float(uq[i]), "count": int(ct[i]), "valid": (float(uq[i]) in GAMUS_VALID_LABELS or int(uq[i]) in GAMUS_VALID_LABELS if float(uq[i]).is_integer() else False)}
        for i in order
    ]
    # `valid` is True only for integer-valued entries within 0..6.
    invalid = sorted({float(v) for v in uq if not (float(v).is_integer() and int(v) in GAMUS_VALID_LABELS)})
    int_valued = bool(((flat == np.round(flat)).all()))
    return {"unique": values, "n_unique": int(len(uq)), "invalid_values": invalid, "integer_valued": int_valued}


def _sentinel_candidates(arr: Any) -> list[dict[str, Any]]:
    """Exact height values repeated over >= SENTINEL_FRACTION of the tile.

    Reported as candidates requiring interpretation — never as confirmed nodata.
    """
    import numpy as np  # type: ignore

    flat = np.asarray(arr).ravel()
    total = int(flat.size)
    if not total:
        return []
    uq, ct = np.unique(flat, return_counts=True)
    thresh = SENTINEL_FRACTION * total
    return [
        {"value": float(uq[i]), "count": int(ct[i]), "fraction": float(ct[i] / total)}
        for i in np.argsort(-ct)
        if ct[i] >= thresh
    ]


def probe_modality(path: Path, modality: str) -> dict[str, Any]:
    """Probe one H5 file; returns stats dict (raises on missing/malformed)."""
    import numpy as np  # type: ignore

    arr, key = _read_h5(path)
    shape = [int(d) for d in np.shape(arr)]
    summary = _summarize_array(arr)
    detail: dict[str, Any] = {
        "modality": modality,
        "path": path.as_posix(),
        "h5_key": key,
        "shape": shape,
        "dtype": str(getattr(arr, "dtype", "unknown")),
        "ndim": int(np.ndim(arr)),
        **summary,
    }
    if modality == "label":
        detail["classes"] = _class_details(arr)
    if modality == "height":
        detail["sentinel_candidates"] = _sentinel_candidates(arr)
    if modality == "image":
        detail["in_uint8_range"] = bool(summary.get("min") is not None and 0.0 <= summary["min"] and summary["max"] <= 255.0)
    return detail


def probe_record(record: GamusRecord, root: Path) -> dict[str, Any]:
    """Probe all modalities of one manifest record; checks spatial alignment."""
    result: dict[str, Any] = {"sample_id": record.sample_id, "split": record.split, "modalities": {}}
    errors: list[str] = []
    for modality, rel in (("image", record.image_path), ("height", record.height_path), ("label", record.label_path)):
        if rel is None:
            result["modalities"][modality] = {"missing": True, "reason": "null path in manifest"}
            continue
        abs_path = root / rel if not Path(rel).is_absolute() else Path(rel)
        if not abs_path.is_file():
            result["modalities"][modality] = {"missing": True, "reason": f"file not found: {abs_path}"}
            errors.append(f"{modality}: missing file {abs_path}")
            continue
        try:
            result["modalities"][modality] = probe_modality(abs_path, modality)
            result["modalities"][modality]["missing"] = False
        except Exception as e:
            result["modalities"][modality] = {"missing": True, "reason": f"{type(e).__name__}: {e}"}
            errors.append(f"{modality}: {type(e).__name__}: {e}")
    # Cross-modality spatial alignment on first two dims (H, W).
    shapes = {
        m: tuple(d["shape"][:2]) for m, d in result["modalities"].items() if not d.get("missing") and d.get("shape")
    }
    if len(shapes) >= 2:
        aligned = len(set(shapes.values())) == 1
    else:
        aligned = len(shapes) <= 1  # vacuous when fewer than 2 modalities present
    result["spatial_shapes"] = {m: list(s) for m, s in shapes.items()}
    result["aligned"] = aligned
    if not aligned:
        errors.append(f"spatial mismatch: {result['spatial_shapes']}")
    result["errors"] = errors
    return result


def probe_records(
    records: Iterable[GamusRecord],
    root: Path | str,
    sample_ids: Optional[Iterable[str]] = None,
    split: Optional[str] = None,
) -> dict[str, Any]:
    """Probe a deterministic subset of records (sorted by sample_id).

    Returns the full report dict. `probe_timestamp_utc` is metadata only and
    plays no role in sample selection.
    """
    from depthwizard.data.schemas import canonical_split

    root = Path(root)
    recs = sorted(list(records), key=lambda r: r.sample_id)
    if split is not None:
        recs = [r for r in recs if r.split == canonical_split(split)]
    if sample_ids is not None:
        wanted = set(sample_ids)
        recs = [r for r in recs if r.sample_id in wanted]
    samples = [probe_record(r, root) for r in recs]
    key_use: dict[str, int] = {}
    for s in samples:
        for m, d in s["modalities"].items():
            if not d.get("missing") and d.get("h5_key"):
                key_use[f"{m}:{d['h5_key']}"] = key_use.get(f"{m}:{d['h5_key']}", 0) + 1
    prefixes: dict[str, int] = {}
    for s in samples:
        prefixes[s["sample_id"].split("_")[0]] = prefixes.get(s["sample_id"].split("_")[0], 0) + 1
    return {
        "tool": "depthwizard.data.probe",
        "probe_timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "root": root.as_posix(),
        "n_samples": len(samples),
        "sample_ids": [s["sample_id"] for s in samples],
        "h5_key_use": key_use,
        "city_prefixes": prefixes,
        "missing_modality_count": sum(
            1 for s in samples for d in s["modalities"].values() if d.get("missing")
        ),
        "mismatched_shape_count": sum(1 for s in samples if not s["aligned"]),
        "samples": samples,
    }


def probe_root(
    root: Path | str,
    sample_ids: Optional[Iterable[str]] = None,
    split: Optional[str] = None,
) -> dict[str, Any]:
    """Discover records under `root` then probe the requested deterministic subset."""
    records = discover_records(Path(root))
    return probe_records(records, Path(root), sample_ids=sample_ids, split=split)


def write_report(report: dict[str, Any], output: Path | str) -> Path:
    """Write compact deterministic JSON report (sorted keys, no raw pixels)."""
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def render_markdown(report: dict[str, Any]) -> str:
    """Render a human-readable Markdown summary generated from `report` numbers."""
    lines = [
        "# GAMUS Empirical Probe — Machine-Generated Summary",
        "",
        f"- Samples: {report['n_samples']} (`{'`, `'.join(report['sample_ids'])}`)",
        f"- Root: `{report['root']}`",
        f"- Probe timestamp (metadata only): {report['probe_timestamp_utc']}",
        f"- H5 key use: `{json.dumps(report['h5_key_use'], sort_keys=True)}`",
        f"- City prefixes in probe: `{json.dumps(report['city_prefixes'], sort_keys=True)}`",
        f"- Missing modalities: {report['missing_modality_count']}; mismatched shapes: {report['mismatched_shape_count']}",
        "",
        "| Sample | Modality | Shape | Dtype | Key | Min | Max | Finite % | NaN | Inf | Neg | Zero | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for s in report["samples"]:
        for mod in ("image", "height", "label"):
            d = s["modalities"].get(mod, {})
            if d.get("missing"):
                lines.append(
                    f"| {s['sample_id']} | {mod} | — | — | — | — | — | — | — | — | — | — | missing: {d.get('reason', '')} |"
                )
                continue
            notes = ""
            if mod == "label" and d.get("classes"):
                uq = [v["value"] for v in d["classes"]["unique"]]
                notes = f"classes={uq}"
                if d["classes"]["invalid_values"]:
                    notes += f" INVALID={d['classes']['invalid_values']}"
            if mod == "height" and d.get("sentinel_candidates"):
                cands = [(c["value"], c["count"]) for c in d["sentinel_candidates"]]
                notes = f"sentinel_candidates={cands}"
            if mod == "image":
                notes = f"uint8_range={d.get('in_uint8_range')}"
            lines.append(
                f"| {s['sample_id']} | {mod} | {d.get('shape')} | {d.get('dtype')} | {d.get('h5_key')} "
                f"| {d.get('min')} | {d.get('max')} | {d.get('finite_pct', 0.0):.2f} | {d.get('nan')} | {d.get('inf')} "
                f"| {d.get('negative')} | {d.get('zero')} | {notes} |"
            )
        lines.append(f"| {s['sample_id']} | alignment | {s.get('spatial_shapes')} | — | — | — | — | — | — | — | — | — | aligned={s.get('aligned')} |")
    lines += ["", "_All numbers above were computed by `depthwizard.data.probe`; see JSON for percentiles and full detail._", ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Probe real GAMUS H5 files and emit JSON + Markdown reports")
    ap.add_argument("--root", type=str, default=None, help="Dataset root (default: GamusConfig resolution)")
    ap.add_argument("--split", type=str, default=None, help="Restrict to split (e.g. train)")
    ap.add_argument("--samples", type=str, nargs="*", default=None, help="Explicit sample IDs (default: all discovered)")
    ap.add_argument("--output", type=str, required=True, help="Output JSON report path")
    ap.add_argument("--markdown", type=str, default=None, help="Optional Markdown summary path")
    args = ap.parse_args()
    root = Path(args.root) if args.root else GamusConfig().resolve_root()
    report = probe_root(root, sample_ids=args.samples, split=args.split)
    write_report(report, args.output)
    print(f"Probed {report['n_samples']} samples -> {args.output}")
    if args.markdown:
        out = Path(args.markdown)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_markdown(report), encoding="utf-8")
        print(f"Wrote summary -> {args.markdown}")


if __name__ == "__main__":
    main()
