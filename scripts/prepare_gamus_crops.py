#!/usr/bin/env python3
"""Add GAMUS (earthflow/GAMUS, CC-BY-4.0) RGB -> AGL crops to the nDSM training set.

GAMUS is the reference dataset recommended for PS 26175. Its tiles are
1024x1024 RGB with per-pixel height above ground (AGL, metres) over
Washington DC, New York and Philadelphia: dense, high-rise urban scenes
that complement the Swiss LiDAR set (diverse landscapes, few towers).

Only the ``train`` split is used (val/test stay untouched for any GAMUS
benchmark). Each tile yields crops at native resolution and 2x coarser,
written in the same .npz format as scripts/prepare_ndsm_dataset.py.

Usage:
  python scripts/prepare_gamus_crops.py --out data/ndsm --tiles 600
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

API = "https://huggingface.co/api/datasets/earthflow/GAMUS"
FILE = "https://huggingface.co/datasets/earthflow/GAMUS/resolve/main/{path}"
#: Nominal GAMUS ground sampling distance (metres), recorded per crop.
GAMUS_GSD = 0.33


def _fetch(url: str, target: Path) -> Path:
    for attempt in range(4):
        try:
            urllib.request.urlretrieve(url, target)
            return target
        except (urllib.error.URLError, OSError):
            if attempt == 3:
                raise
            time.sleep(2 + 3 * attempt)
    return target


def _read(path: Path) -> np.ndarray:
    import h5py

    with h5py.File(path, "r") as handle:
        return np.asarray(handle["image"][()])


def _downsample(rgb: np.ndarray, agl: np.ndarray, factor: int) -> tuple[np.ndarray, np.ndarray]:
    h, w = (rgb.shape[0] // factor) * factor, (rgb.shape[1] // factor) * factor
    r = rgb[:h, :w].reshape(h // factor, factor, w // factor, factor, 3).mean(axis=(1, 3))
    a = agl[:h, :w].reshape(h // factor, factor, w // factor, factor).mean(axis=(1, 3))
    return r.astype(np.uint8), a.astype(np.float32)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/ndsm")
    parser.add_argument("--raw", default="data/gamus_raw")
    parser.add_argument("--tiles", type=int, default=600)
    parser.add_argument("--crop", type=int, default=392)
    parser.add_argument("--seed", type=int, default=26175)
    args = parser.parse_args(argv)
    out, raw = Path(args.out), Path(args.raw)
    out.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    with urllib.request.urlopen(API, timeout=60) as response:
        names = [s["rfilename"] for s in json.load(response)["siblings"]]
    stems = sorted(
        n[len("images/train/") : -len("_RGB.h5")]
        for n in names
        if n.startswith("images/train/") and n.endswith("_RGB.h5")
    )
    by_city: dict[str, list[str]] = {}
    for stem in stems:
        by_city.setdefault(stem.split("_")[0], []).append(stem)
    per_city = max(1, args.tiles // len(by_city))
    chosen = [s for city in by_city.values() for s in rng.permutation(city)[:per_city]]

    written = 0
    for i, stem in enumerate(chosen):
        if any(out.glob(f"gamus_{stem}_*.npz")):
            continue  # resumable
        rgb_file = raw / f"{stem}_RGB.h5"
        agl_file = raw / f"{stem}_AGL.h5"
        try:
            _fetch(FILE.format(path=f"images/train/{stem}_RGB.h5"), rgb_file)
            _fetch(FILE.format(path=f"heights/train/{stem}_AGL.h5"), agl_file)
            rgb = _read(rgb_file).astype(np.uint8)
            agl = np.clip(np.nan_to_num(_read(agl_file).astype(np.float32)), 0.0, 400.0)
            for factor in (1, 2):
                r, a = (rgb, agl) if factor == 1 else _downsample(rgb, agl, factor)
                if min(a.shape) < args.crop:
                    continue
                for j in range(2 if factor == 1 else 1):
                    top = int(rng.integers(0, a.shape[0] - args.crop + 1))
                    left = int(rng.integers(0, a.shape[1] - args.crop + 1))
                    np.savez_compressed(
                        out / f"gamus_{stem}_{factor}x_{j}.npz",
                        rgb=r[top : top + args.crop, left : left + args.crop],
                        ndsm=a[top : top + args.crop, left : left + args.crop].astype(np.float16),
                        gsd=np.float32(GAMUS_GSD * factor),
                        landscape="urban",
                        tile=stem,
                    )
                    written += 1
        except Exception as exc:
            print(json.dumps({"tile": stem, "error": f"{type(exc).__name__}: {exc}"}), flush=True)
        finally:
            rgb_file.unlink(missing_ok=True)
            agl_file.unlink(missing_ok=True)
        if i % 50 == 0:
            print(json.dumps({"progress": i, "of": len(chosen), "crops": written}), flush=True)
    print(json.dumps({"total_new_crops": written}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
