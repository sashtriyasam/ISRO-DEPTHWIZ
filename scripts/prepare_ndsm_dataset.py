#!/usr/bin/env python3
"""Build an RGB -> nDSM (height above ground, metres) training set from open LiDAR.

Sources (swisstopo open data, no key):
* SWISSIMAGE 10 cm orthophoto          -> RGB at several ground sampling distances;
* swissSURFACE3D 0.5 m (LiDAR DSM) minus swissALTI3D 0.5 m (LiDAR DTM)
                                       -> nDSM target (buildings, trees, structures).

Training on nDSM teaches the backbone metric structure heights, which the
DEM-anchored fusion adds to the reference DEM (terrain comes from the DEM,
structures from the model). GSDs span 0.35-2 m so the model is not tied to
one resolution (PS FAQ: evaluation imagery 0.35-10 m; do not overfit 0.6 m).

Benchmark sites (scripts/benchmark_swiss.py) are excluded with a 2 km guard
so the accuracy benchmark stays held-out.

Usage:
  python scripts/prepare_ndsm_dataset.py --out data/ndsm --crop 392
Raw downloads are deleted after cropping (disk budget); crops are .npz.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark_swiss import SITES as BENCHMARK_SITES  # noqa: E402

STAC = "https://data.geo.admin.ch/api/stac/v0.9/collections"
IMAGE = ("ch.swisstopo.swissimage-dop10", "_0.1_2056.tif")
DSM = ("ch.swisstopo.swisssurface3d-raster", "_0.5_2056_5728.tif")
DTM = ("ch.swisstopo.swissalti3d", "_0.5_2056_5728.tif")

#: (name, class, lon, lat) seeds spread over Swiss landscapes.
TRAIN_SITES: list[tuple[str, str, float, float]] = [
    ("geneva", "urban", 6.1430, 46.2040),
    ("lausanne", "urban", 6.6320, 46.5200),
    ("basel", "urban", 7.5890, 47.5600),
    ("lucerne", "urban", 8.3090, 47.0500),
    ("stgallen", "urban", 9.3770, 47.4240),
    ("lugano", "urban", 8.9510, 46.0040),
    ("winterthur", "urban", 8.7240, 47.5000),
    ("biel", "urban", 7.2470, 47.1370),
    ("zurich_oerlikon", "urban", 8.5440, 47.4110),
    ("fribourg", "urban", 7.1600, 46.8060),
    ("thun", "urban", 7.6280, 46.7580),
    ("chur", "urban", 9.5300, 46.8500),
    ("broye_fields", "sparse", 6.9600, 46.7600),
    ("thurgau_fields", "sparse", 9.0800, 47.5600),
    ("aargau_fields", "sparse", 8.1500, 47.3900),
    ("vaud_vineyards", "sparse", 6.7600, 46.4900),
    ("seeland_fields", "sparse", 7.0700, 46.9900),
    ("emmental_forest", "forested", 7.7800, 46.9700),
    ("jura_forest", "forested", 6.9900, 47.3500),
    ("napf_forest", "forested", 7.9400, 47.0100),
    ("schwarzwald_border", "forested", 8.3300, 47.6100),
    ("ticino_forest", "forested", 8.8000, 46.2000),
    ("sihl_forest_north", "forested", 8.5300, 47.2900),
    ("zermatt", "hilly", 7.7480, 46.0200),
    ("davos", "hilly", 9.8370, 46.8030),
    ("engadin", "hilly", 9.8400, 46.4980),
    ("grindelwald", "hilly", 8.0400, 46.6240),
    ("valais_slopes", "hilly", 7.3600, 46.2300),
    ("toggenburg", "hilly", 9.1700, 47.2300),
    ("gruyere", "hilly", 7.0800, 46.5800),
    ("glarus", "hilly", 9.0670, 47.0400),
    ("leventina", "hilly", 8.8100, 46.4400),
]

GSDS = (0.35, 0.6, 1.0, 2.0)
GUARD_DEG = 0.03  # ~2-3 km exclusion around benchmark sites


def _near_benchmark(lon: float, lat: float) -> bool:
    return any(abs(lon - b[2]) < GUARD_DEG and abs(lat - b[3]) < GUARD_DEG for b in BENCHMARK_SITES)


def _asset(collection: str, suffix: str, lon: float, lat: float) -> tuple[str, str]:
    bbox = f"{lon - 0.0005},{lat - 0.0005},{lon + 0.0005},{lat + 0.0005}"
    with urllib.request.urlopen(f"{STAC}/{collection}/items?bbox={bbox}&limit=10", timeout=60) as r:
        items = json.load(r)["features"]
    if not items:
        raise RuntimeError(f"no {collection} item")
    items.sort(key=lambda f: f["id"], reverse=True)
    tile = items[0]["id"].split("_")[-1]  # e.g. 2599-1198
    for asset in items[0]["assets"].values():
        if asset["href"].endswith(suffix):
            return str(asset["href"]), tile
    raise RuntimeError(f"no {suffix} asset")


def _download(url: str, target: Path) -> Path:
    if target.is_file():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".part")
    for attempt in range(4):
        try:
            urllib.request.urlretrieve(url, tmp)
            break
        except (urllib.error.ContentTooShortError, OSError):
            if attempt == 3:
                raise
            time.sleep(2 + 3 * attempt)
    tmp.replace(target)
    return target


def _read(path: Path, gsd: float, bands: list[int]) -> tuple[np.ndarray, float]:
    import rasterio
    from rasterio.enums import Resampling

    with rasterio.open(path) as src:
        scale = src.res[0] / gsd
        h = max(1, int(round(src.height * scale)))
        w = max(1, int(round(src.width * scale)))
        data = src.read(bands, out_shape=(len(bands), h, w), resampling=Resampling.average)
        nodata = src.nodata
    data = data.astype(np.float32)
    if nodata is not None:
        data[data == nodata] = np.nan
    return data, scale


def process_site(
    site: tuple[str, str, float, float], out: Path, raw: Path, crop: int, rng: np.random.Generator
) -> int:
    name, landscape, lon, lat = site
    image_url, tile = _asset(IMAGE[0], IMAGE[1], lon, lat)
    dsm_url, _ = _asset(DSM[0], DSM[1], lon, lat)
    dtm_url, _ = _asset(DTM[0], DTM[1], lon, lat)
    folder = raw / name
    image = _download(image_url, folder / "ortho.tif")
    dsm = _download(dsm_url, folder / "dsm.tif")
    dtm = _download(dtm_url, folder / "dtm.tif")
    written = 0
    for gsd in GSDS:
        rgb, _ = _read(image, gsd, [1, 2, 3])
        surface, _ = _read(dsm, gsd, [1])
        terrain, _ = _read(dtm, gsd, [1])
        h = min(rgb.shape[1], surface.shape[1], terrain.shape[1])
        w = min(rgb.shape[2], surface.shape[2], terrain.shape[2])
        rgb = rgb[:, :h, :w]
        ndsm = np.clip(surface[0, :h, :w] - terrain[0, :h, :w], 0.0, 300.0)
        if h < crop or w < crop:
            continue
        count = max(1, int(round((h * w) / (crop * crop) * 1.5)))
        for i in range(count):
            r = int(rng.integers(0, h - crop + 1))
            c = int(rng.integers(0, w - crop + 1))
            patch = ndsm[r : r + crop, c : c + crop]
            if not np.isfinite(patch).mean() > 0.98:
                continue
            np.savez_compressed(
                out / f"{name}_{gsd:g}m_{i:02d}.npz",
                rgb=np.clip(
                    np.transpose(rgb[:, r : r + crop, c : c + crop], (1, 2, 0)), 0, 255
                ).astype(np.uint8),
                ndsm=np.nan_to_num(patch, nan=0.0).astype(np.float16),
                gsd=np.float32(gsd),
                landscape=landscape,
                tile=tile,
            )
            written += 1
    for f in (image, dsm, dtm):
        f.unlink(missing_ok=True)  # disk budget: crops are all we keep
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/ndsm")
    parser.add_argument("--raw", default="data/ndsm_raw")
    parser.add_argument("--crop", type=int, default=392)
    parser.add_argument("--seed", type=int, default=26175)
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    total = 0
    for site in TRAIN_SITES:
        if _near_benchmark(site[2], site[3]):
            print(json.dumps({"site": site[0], "skipped": "near benchmark site"}), flush=True)
            continue
        if any(out.glob(f"{site[0]}_*.npz")):
            continue  # resumable
        try:
            n = process_site(site, out, Path(args.raw), args.crop, rng)
            total += n
            print(json.dumps({"site": site[0], "crops": n}), flush=True)
        except Exception as exc:
            print(
                json.dumps({"site": site[0], "error": f"{type(exc).__name__}: {exc}"}), flush=True
            )
    print(json.dumps({"total_new_crops": total}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
