"""
Deterministic manifest generation for GAMUS.

Guarantees:
    same input (root + config) -> same manifest (byte-identical ordering)
    ordering deterministic: sorted by (split, sample_id)
    no filesystem-order dependence (explicit sort)
    no random iteration, no hash randomization beyond controlled seed, no timestamp dependence

Each record contains: sample_id, image_path, height_path, label_path, split, source, checksum (optional),
dimensions/dtype if inspectable.

Only fields supported by actual dataset are emitted; no invented metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable, Optional

from depthwizard.data.schemas import (
    GAMUS_SPLITS,
    GamusRecord,
    _strip_image_suffix,
    canonical_split,
    expected_height_filename,
    expected_label_filename,
)

MANIFEST_VERSION = "1.0"


def _safe_checksum(path: Path, limit_bytes: int = 8_000_000) -> Optional[str]:
    """Return sha256 hex of file content if practical, else None.

    Practical: file exists and size <= limit_bytes (default 8MB, fits typical 4.2MB H5).
    Uses chunked reading to avoid large memory.
    """
    try:
        if not path.is_file():
            return None
        size = path.stat().st_size
        if size > limit_bytes:
            return None
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _try_probe_h5(path: Path) -> tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
    """Try to probe an H5 file for dtype and spatial dimensions without requiring h5py at import time.

    Returns (dtype_str, width, height, key_used) or (None,None,None,None) if unavailable.
    Handles both 'image' and 'data' keys (see audit: legacy uses 'data', current uses 'image').
    """
    try:
        import h5py  # type: ignore
    except Exception:
        return (None, None, None, None)
    if not path.is_file():
        return (None, None, None, None)
    try:
        with h5py.File(str(path), "r") as f:
            # Prefer 'image' then 'data', else first dataset
            key = None
            if "image" in f:
                key = "image"
            elif "data" in f:
                key = "data"
            else:
                # fallback: first dataset key
                for k in f.keys():
                    # check if dataset
                    try:
                        if hasattr(f[k], "shape"):
                            key = k
                            break
                    except Exception:
                        continue
                if key is None:
                    return (None, None, None, None)
            dset = f[key]
            arr = dset[()] if hasattr(dset, "__getitem__") else None
            # arr may be 0-d? Just inspect shape/dtype via dset attrs
            shape = getattr(dset, "shape", None) or getattr(arr, "shape", None)
            dtype = getattr(dset, "dtype", None) or getattr(arr, "dtype", None)
            dtype_str = str(dtype) if dtype is not None else None
            h = w = None
            if shape is not None and len(shape) >= 2:
                # Expect (H,W) or (H,W,C)
                h, w = int(shape[0]), int(shape[1])
            return (dtype_str, w, h, key)
    except Exception:
        return (None, None, None, None)


def discover_records(
    root: Path | str,
    splits: Optional[Iterable[str]] = None,
    probe: bool = False,
    checksum: bool = False,
) -> list[GamusRecord]:
    """Discover GamusRecords under `root`.

    Args:
        root: dataset root containing images/{split} etc.
        splits: iterable of splits to scan (defaults to GAMUS_SPLITS order, deterministic).
        probe: if True, attempt to read H5 headers for dtype/dimensions (requires h5py).
        checksum: if True, compute sha256 of image files when practical.

    Returns:
        Sorted list of GamusRecord (by split order then sample_id lexicographically).
    """
    root = Path(root)
    if splits is None:
        splits = GAMUS_SPLITS
    else:
        splits = [canonical_split(s) for s in splits]

    # Preserve canonical split ordering for determinism regardless of input order
    split_order = {s: i for i, s in enumerate(GAMUS_SPLITS)}
    splits_sorted = sorted(splits, key=lambda s: split_order.get(s, 99))

    records: list[GamusRecord] = []
    for split in splits_sorted:
        image_dir = root / "images" / split
        height_dir = root / "heights" / split
        label_dir = root / "classes" / split
        if not image_dir.is_dir():
            # Missing split directory — skip, not error (allows fixture-based operation)
            continue
        # Deterministic enumeration: sorted filenames
        try:
            files = sorted(os.listdir(image_dir))
        except FileNotFoundError:
            continue
        # Filter to .h5 files and stable sort
        image_files = sorted([f for f in files if f.endswith(".h5")])
        for img_file in image_files:
            sample_id = _strip_image_suffix(img_file)
            if sample_id is None or not sample_id:
                # Not an image-like file; skip with traceable sample_id fallback
                sample_id = img_file[:-3] if img_file.endswith(".h5") else img_file
                # If still contains suffix markers, skip to avoid false pairing
                if "CLS" in sample_id or "AGL" in sample_id:
                    continue
            # Expected counterpart filenames (canonical RGB form)
            # Note: label/heights use deterministic derived names
            height_filename = expected_height_filename(sample_id)
            label_filename = expected_label_filename(sample_id)

            image_rel = Path("images") / split / img_file
            height_rel = Path("heights") / split / height_filename
            label_rel = Path("classes") / split / label_filename

            # Check if label exists on filesystem to decide whether to include (test split may exist anyway)
            label_abs = root / label_rel
            # Emit label_path as string regardless; validation will flag missing, but manifest preserves pairing intent
            # To avoid spurious missing for distributions lacking test labels, we still emit but set None if truly absent and probe shows no file?
            # Task says only include fields supported by actual dataset — label_path is supported, but we include as nullable.
            # We emit path if file exists or if split may have labels; else None is allowed but we default to emitting for consistency.
            # Decision: emit label Rel string if either file exists or split != "test"? For determinism we always emit, but allow None override via caller.
            label_rel_str: Optional[str] = label_rel.as_posix()
            # If we want to emit None when file definitely doesn't exist and caller wants minimal, we keep string; validation will report.
            # Keep string for pairing logic.

            image_abs = root / image_rel
            height_abs = root / height_rel

            # Optional enrichments
            cs: Optional[str] = None
            if checksum:
                cs = _safe_checksum(image_abs)

            img_dtype = h_dtype = None
            w = h = None
            if probe:
                img_dtype, w, h, _ = _try_probe_h5(image_abs)
                h_dtype, _, _, _ = _try_probe_h5(height_abs)
                # Note: we reuse w,h from image probe; height should match but we trust image as source
                # If probe needed for height dimensions separately, we could store width_h/height_h but schema only has one.

            rec = GamusRecord(
                sample_id=sample_id,
                image_path=image_rel.as_posix(),
                height_path=height_rel.as_posix(),
                label_path=label_rel_str,
                split=split,
                source="gamus",
                checksum=cs,
                image_dtype=img_dtype,
                height_dtype=h_dtype,
                width=w,
                height=h,
            )
            records.append(rec)

    # Final deterministic ordering: split order then sample_id
    records.sort(key=lambda r: (split_order.get(r.split, 99), r.sample_id))
    return records


def build_manifest(
    root: Path | str,
    output_path: Optional[Path | str] = None,
    splits: Optional[Iterable[str]] = None,
    probe: bool = False,
    checksum: bool = False,
) -> dict:
    """Build a manifest dict and optionally write to JSON file deterministically.

    Returns the manifest dict (also written if output_path provided).
    """
    records = discover_records(root, splits=splits, probe=probe, checksum=checksum)
    manifest = {
        "version": MANIFEST_VERSION,
        "source": "gamus",
        "root": Path(root).as_posix(),
        "records": [r.to_dict() for r in records],
    }
    # Deterministic JSON: sort_keys, indent 2, ensure ascii etc, but records already sorted
    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        # Write deterministically: sort_keys True, indent 2, ensure trailing newline
        out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def load_manifest(path: Path | str) -> dict:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    # Canonicalize order of records by deterministic key (for consumers that may have written unsorted)
    records = data.get("records", [])
    # Validate and re-sort deterministically to defend against filesystem/malformed ordering
    from depthwizard.data.schemas import GamusRecord

    parsed = [GamusRecord.from_dict(r) for r in records]
    split_order = {s: i for i, s in enumerate(GAMUS_SPLITS)}
    parsed.sort(key=lambda r: (split_order.get(r.split, 99), r.sample_id))
    data["records"] = [r.to_dict() for r in parsed]
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description="Build deterministic GAMUS manifest")
    ap.add_argument("--root", type=str, required=True, help="Dataset root (contains images/, heights/, classes/)")
    ap.add_argument("--output", type=str, required=True, help="Output manifest JSON path")
    ap.add_argument(
        "--splits",
        type=str,
        nargs="*",
        default=None,
        help="Splits to include (default all: train val test)",
    )
    ap.add_argument("--probe", action="store_true", help="Probe H5 headers for dtype/dimensions (requires h5py)")
    ap.add_argument("--checksum", action="store_true", help="Compute sha256 of image files when practical")
    args = ap.parse_args()
    build_manifest(args.root, args.output, splits=args.splits, probe=args.probe, checksum=args.checksum)
    print(f"Wrote manifest to {args.output}")


if __name__ == "__main__":
    main()
