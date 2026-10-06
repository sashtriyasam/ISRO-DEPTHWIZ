#!/usr/bin/env python3
"""Coarse-GSD (4-10 m) RGB -> nDSM crops from 5x5 km swisstopo mosaics.

PS 26175 evaluates imagery from 0.35 m to 10 m. scripts/prepare_ndsm_dataset.py
covers 0.35-2 m from single 1 km tiles; a 392 px crop at 10 m spans 3.9 km,
so here each training seed becomes a 5x5 km mosaic of 1 km tiles:

* SWISSIMAGE 2 m orthophoto (the collection's own 2 m product);
* swissSURFACE3D 0.5 m LiDAR DSM, averaged to 2 m;
* swissALTI3D 2 m LiDAR DTM.

The 2 m mosaic is block-averaged (NaN-aware) to 4 / 6 / 8 / 10 m, and the
target is nDSM = DSM - DTM at that GSD (the mean surface height per pixel,
the same averaging the benchmark applies to its LiDAR truth). Crops use the
same .npz format and site-name prefix as the fine set, so train_ndsm.py's
whole-site validation split applies unchanged.

Seeds whose mosaic could touch a benchmark site are skipped (wider guard
than the fine set: the mosaic itself is 5 km across).

Usage:
  python scripts/prepare_ndsm_coarse.py --out data/ndsm_coarse
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark_swiss import SITES as BENCHMARK_SITES  # noqa: E402
from benchmark_swiss import _stac_asset  # noqa: E402
from prepare_ndsm_dataset import TRAIN_SITES  # noqa: E402

IMAGE = ("ch.swisstopo.swissimage-dop10", "_2_2056.tif")
DSM = ("ch.swisstopo.swisssurface3d-raster", "_0.5_2056_5728.tif")
DTM = ("ch.swisstopo.swissalti3d", "_2_2056_5728.tif")
BASE_GSD = 2.0
TILE_PX = 500  # 1 km at 2 m
GSDS = (4.0, 6.0, 8.0, 10.0)
#: Mosaic half-width is 2.5 km; keep >= ~6 km from any benchmark tile.
GUARD_DEG = 0.08


def _near_benchmark(lon: float, lat: float) -> bool:
    return any(abs(lon - b[2]) < GUARD_DEG and abs(lat - b[3]) < GUARD_DEG for b in BENCHMARK_SITES)


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


def _read_2m(path: Path, bands: list[int]) -> np.ndarray:
    """Read a 1 km tile onto the 500x500 2 m grid (average when downsampling)."""
    import rasterio
    from rasterio.enums import Resampling

    with rasterio.open(path) as src:
        data = src.read(
            bands, out_shape=(len(bands), TILE_PX, TILE_PX), resampling=Resampling.average
        ).astype(np.float32)
        if src.nodata is not None:
            data[data == src.nodata] = np.nan
    return data


def _tile_center_lonlat(e_km: int, n_km: int) -> tuple[float, float]:
    from rasterio.warp import transform

    lons, lats = transform("EPSG:2056", "EPSG:4326", [e_km * 1000 + 500], [n_km * 1000 + 500])
    return float(lons[0]), float(lats[0])


def _fetch_tile(e_km: int, n_km: int, raw: Path) -> tuple[int, int, dict[str, np.ndarray] | None]:
    lon, lat = _tile_center_lonlat(e_km, n_km)
    folder = raw / f"{e_km}-{n_km}"
    try:
        files = {
            key: _download(_stac_asset(coll, lon, lat, suffix), folder / f"{key}.tif")
            for key, (coll, suffix) in (("rgb", IMAGE), ("dsm", DSM), ("dtm", DTM))
        }
        layers = {
            "rgb": _read_2m(files["rgb"], [1, 2, 3]),
            "dsm": _read_2m(files["dsm"], [1])[0],
            "dtm": _read_2m(files["dtm"], [1])[0],
        }
    except Exception:
        return e_km, n_km, None  # missing tile (border, lake): stays NaN in the mosaic
    finally:
        for f in folder.glob("*"):
            f.unlink(missing_ok=True)
    return e_km, n_km, layers


def _block_mean(a: np.ndarray, k: int) -> np.ndarray:
    """NaN-aware block mean over the last two axes."""
    h, w = (a.shape[-2] // k) * k, (a.shape[-1] // k) * k
    b = a[..., :h, :w].reshape(*a.shape[:-2], h // k, k, w // k, k)
    valid = np.isfinite(b)
    total = np.where(valid, b, 0.0).sum(axis=(-3, -1))
    count = valid.sum(axis=(-3, -1))
    out = total / np.maximum(count, 1)
    out[count < (k * k) // 2] = np.nan
    return out.astype(np.float32)


def process_site(
    site: tuple[str, str, float, float],
    out: Path,
    raw: Path,
    crop: int,
    span: int,
    rng: np.random.Generator,
    workers: int = 6,
) -> int:
    from rasterio.warp import transform

    name, landscape, lon, lat = site
    xs, ys = transform("EPSG:4326", "EPSG:2056", [lon], [lat])
    e0, n0 = int(xs[0] // 1000) - span // 2, int(ys[0] // 1000) - span // 2
    size = span * TILE_PX
    rgb = np.full((3, size, size), np.nan, dtype=np.float32)
    dsm = np.full((size, size), np.nan, dtype=np.float32)
    dtm = np.full((size, size), np.nan, dtype=np.float32)
    jobs = [(e0 + i, n0 + j) for i in range(span) for j in range(span)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for e_km, n_km, layers in pool.map(lambda t: _fetch_tile(*t, raw), jobs):
            if layers is None:
                continue
            # LV95 north is up: row 0 of the mosaic is the northernmost tile.
            r = (n0 + span - 1 - n_km) * TILE_PX
            c = (e_km - e0) * TILE_PX
            rgb[:, r : r + TILE_PX, c : c + TILE_PX] = layers["rgb"]
            dsm[r : r + TILE_PX, c : c + TILE_PX] = layers["dsm"]
            dtm[r : r + TILE_PX, c : c + TILE_PX] = layers["dtm"]

    written = 0
    for gsd in GSDS:
        k = int(round(gsd / BASE_GSD))
        g_rgb = _block_mean(rgb, k)
        g_ndsm = np.clip(_block_mean(dsm, k) - _block_mean(dtm, k), 0.0, 300.0)
        h, w = g_ndsm.shape
        if h < crop or w < crop:
            continue
        count = max(1, int(round((h * w) / (crop * crop) * 1.5)))
        for i in range(count):
            r = int(rng.integers(0, h - crop + 1))
            c = int(rng.integers(0, w - crop + 1))
            patch = g_ndsm[r : r + crop, c : c + crop]
            image = g_rgb[:, r : r + crop, c : c + crop]
            if not (np.isfinite(patch).mean() > 0.98 and np.isfinite(image).mean() > 0.98):
                continue
            # Orthophoto tiles are black (0, not nodata) outside Swiss coverage.
            if (np.nan_to_num(image).sum(axis=0) < 1.0).mean() > 0.01:
                continue
            np.savez_compressed(
                out / f"{name}_c{gsd:g}m_{i:02d}.npz",
                rgb=np.clip(np.nan_to_num(np.transpose(image, (1, 2, 0))), 0, 255).astype(np.uint8),
                ndsm=np.nan_to_num(patch, nan=0.0).astype(np.float16),
                gsd=np.float32(gsd),
                landscape=landscape,
                tile=f"{e0}-{n0}x{span}",
            )
            written += 1
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/ndsm_coarse")
    parser.add_argument("--raw", default="data/ndsm_coarse_raw")
    parser.add_argument("--crop", type=int, default=392)
    parser.add_argument("--span", type=int, default=5, help="mosaic size in 1 km tiles")
    parser.add_argument("--seed", type=int, default=26176)
    parser.add_argument("--workers", type=int, default=6, help="parallel tile downloads")
    parser.add_argument("--sites", nargs="*", help="limit to these seed names")
    args = parser.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    total = 0
    for site in TRAIN_SITES:
        if args.sites and site[0] not in args.sites:
            continue
        if _near_benchmark(site[2], site[3]):
            print(json.dumps({"site": site[0], "skipped": "near benchmark site"}), flush=True)
            continue
        if any(out.glob(f"{site[0]}_c*.npz")):
            continue  # resumable
        started = time.perf_counter()
        try:
            n = process_site(site, out, Path(args.raw), args.crop, args.span, rng, args.workers)
            total += n
            print(
                json.dumps(
                    {"site": site[0], "crops": n, "seconds": round(time.perf_counter() - started)}
                ),
                flush=True,
            )
        except Exception as exc:
            print(
                json.dumps({"site": site[0], "error": f"{type(exc).__name__}: {exc}"}), flush=True
            )
    print(json.dumps({"total_new_crops": total}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
