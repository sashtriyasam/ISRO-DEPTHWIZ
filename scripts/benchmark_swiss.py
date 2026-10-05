#!/usr/bin/env python3
"""Accuracy benchmark against airborne LiDAR (swisstopo open data).

Reference data (open, no key, data.geo.admin.ch STAC):
* imagery  — SWISSIMAGE 10 cm orthophoto, resampled to Cartosat-like GSDs;
* truth    — swissSURFACE3D 0.5 m LiDAR DSM (absolute heights, LN02/LHN95).

For every site and GSD the script runs the depth model, then scores
several DSM products against the LiDAR DSM (and against the Copernicus
DEM, which is what the PS 26175 evaluation compares to):

* ``copernicus``   — Copernicus GLO-30 resampled bilinearly (no model);
* ``fusion``       — DEM-anchored fusion with the fitted detail scale;
* ``affine``       — legacy scale+offset fit of relative depth to the DEM;
* ``fusion_oracle``— fusion with the detail scale fitted to the LiDAR
                     (upper bound for the detail term; not deployable).

Usage:
  python scripts/benchmark_swiss.py --out data/benchmarks/swiss \\
      [--gsd 0.6 2.0] [--sites urban_zurich forest_sihlwald] [--tiled]

Downloads are cached under --out; nothing is committed (*.tif ignored).
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

STAC = "https://data.geo.admin.ch/api/stac/v0.9/collections"
IMAGE_COLLECTION = "ch.swisstopo.swissimage-dop10"
DSM_COLLECTION = "ch.swisstopo.swisssurface3d-raster"

#: (site id, landscape class, lon, lat) — one 1 km tile each.
SITES: list[tuple[str, str, float, float]] = [
    ("urban_zurich", "urban", 8.5400, 47.3780),
    ("urban_bern", "urban", 7.4440, 46.9480),
    ("sparse_avenches", "sparse", 7.0300, 46.8800),
    ("sparse_seeland", "sparse", 7.2200, 47.0200),
    ("hilly_lauterbrunnen", "hilly", 7.9100, 46.5900),
    ("hilly_appenzell", "hilly", 9.4100, 47.3300),
    ("forest_sihlwald", "forested", 8.5550, 47.2550),
    ("forest_jura", "forested", 7.1300, 47.2600),
]


def _stac_asset(collection: str, lon: float, lat: float, suffix: str) -> str:
    bbox = f"{lon - 0.0005},{lat - 0.0005},{lon + 0.0005},{lat + 0.0005}"
    url = f"{STAC}/{collection}/items?bbox={bbox}&limit=10"
    with urllib.request.urlopen(url, timeout=60) as response:
        items = json.load(response)["features"]
    if not items:
        raise RuntimeError(f"no {collection} item at {lon},{lat}")
    items.sort(key=lambda f: f["id"], reverse=True)  # newest acquisition first
    for asset in items[0]["assets"].values():
        if asset["href"].endswith(suffix):
            return str(asset["href"])
    raise RuntimeError(f"no {suffix} asset in {items[0]['id']}")


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


def _resample_image(source: Path, gsd: float, target: Path) -> Path:
    """Average-resample the orthophoto to ``gsd`` metres (RGB uint8 GeoTIFF)."""
    import rasterio
    from rasterio.enums import Resampling

    if target.is_file():
        return target
    with rasterio.open(source) as src:
        scale = src.res[0] / gsd
        width = int(round(src.width * scale))
        height = int(round(src.height * scale))
        data = src.read(
            indexes=[1, 2, 3], out_shape=(3, height, width), resampling=Resampling.average
        )
        transform = src.transform * src.transform.scale(src.width / width, src.height / height)
        profile = src.profile.copy()
    profile.update(
        width=width,
        height=height,
        count=3,
        dtype="uint8",
        transform=transform,
        compress="deflate",
        photometric="RGB",
    )
    profile.pop("nodata", None)
    with rasterio.open(target, "w", **profile) as dst:
        dst.write(data)
    return target


def _align(path: Path, like_transform, like_crs, shape: tuple[int, int]) -> np.ndarray:  # type: ignore[no-untyped-def]
    """Resample a raster onto the image grid (average for downsampling)."""
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import reproject

    out = np.full(shape, np.nan, dtype=np.float64)
    with rasterio.open(path) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=out,
            src_nodata=src.nodata,
            dst_transform=like_transform,
            dst_crs=like_crs,
            dst_nodata=np.nan,
            resampling=Resampling.average,
        )
    return out


def _metrics(pred: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    ok = np.isfinite(pred) & np.isfinite(truth)
    p, t = pred[ok], truth[ok]
    err = p - t
    r = float(np.corrcoef(p, t)[0, 1]) if p.size > 2 and p.std() > 0 and t.std() > 0 else 0.0
    return {
        "rmse": float(np.sqrt(np.mean(err**2))),
        "mae": float(np.mean(np.abs(err))),
        "bias": float(np.mean(err)),
        "pearson_r": r,
        "n": int(ok.sum()),
    }


def _block(a: np.ndarray, k: int) -> np.ndarray:
    """Mean over k x k blocks (truncated edges), NaN-aware."""
    h, w = (a.shape[0] // k) * k, (a.shape[1] // k) * k
    b = a[:h, :w].reshape(h // k, k, w // k, k)
    with np.errstate(invalid="ignore"):
        return np.nanmean(np.nanmean(b, axis=3), axis=1)


def _depth(image: Path, tiled: bool) -> np.ndarray:
    from depthwizard.backends.depth_anything_v2 import DepthAnythingV2Backend
    from depthwizard.ingestion.api import inspect_input

    backend = DepthAnythingV2Backend()
    inspection = inspect_input(image)
    if not tiled:
        depth = backend.estimate_depth(inspection)
        return np.asarray(depth.depth_values, dtype=np.float64).reshape(
            depth.output_resolution.height, depth.output_resolution.width
        )
    from depthwizard.backends.satellite import _tiled_infer_image
    from depthwizard.ingestion.pixels import load_model_rgb

    backend.load()
    rgb = load_model_rgb(inspection).rgb
    bgr = rgb[:, :, ::-1].copy()
    return np.asarray(_tiled_infer_image(backend._model, bgr, 518), dtype=np.float64)


def run_site(
    site: tuple[str, str, float, float], out: Path, gsds: list[float], tiled: bool
) -> list[dict]:  # type: ignore[type-arg]
    import rasterio

    from depthwizard.calibration.fusion import dem_anchored_calibration, dem_pixels_in_image
    from depthwizard.contracts.semantics import ElevationSemantics
    from depthwizard.dem.auto import fetch_reference_dem
    from depthwizard.ingestion.api import inspect_input

    site_id, landscape, lon, lat = site
    folder = out / site_id
    ortho = _download(
        _stac_asset(IMAGE_COLLECTION, lon, lat, "_0.1_2056.tif"), folder / "ortho_0.1.tif"
    )
    lidar = _download(
        _stac_asset(DSM_COLLECTION, lon, lat, "_0.5_2056_5728.tif"), folder / "lidar_dsm_0.5.tif"
    )
    rows: list[dict] = []  # type: ignore[type-arg]
    for gsd in gsds:
        image = _resample_image(ortho, gsd, folder / f"image_{gsd:g}m.tif")
        with rasterio.open(image) as ds:
            transform, crs, shape = ds.transform, ds.crs, (ds.height, ds.width)
        truth = _align(lidar, transform, crs, shape)
        inspection = inspect_input(image)
        dem_path = fetch_reference_dem(inspection).path
        dem = _align_bilinear(dem_path, transform, crs, shape)
        started = time.perf_counter()
        rel = _depth(image, tiled)
        infer_s = time.perf_counter() - started
        valid = np.isfinite(rel)
        k = dem_pixels_in_image(30.0, gsd)
        target = ElevationSemantics.ABSOLUTE_ELEVATION_DSM

        cal, _ = dem_anchored_calibration(
            rel,
            valid,
            dem,
            np.isfinite(dem),
            k,
            reference_id="copernicus",
            target=target,
            source_checksum=None,
        )
        s_fit = cal.scale
        # Oracle detail scale: least squares of (truth - DEM) on (rel - lowpass(rel)).
        from depthwizard.calibration.fusion import box_mean

        detail = rel - box_mean(rel, valid, k)
        ok = np.isfinite(detail) & np.isfinite(truth) & np.isfinite(dem)
        resid = (truth - dem)[ok]
        d = detail[ok]
        s_oracle = float(np.dot(d, resid) / np.dot(d, d)) if np.dot(d, d) > 0 else 0.0
        product_oracle = dem + s_oracle * detail
        product_fusion = dem + s_fit * detail
        # Legacy affine fit of relative depth to the DEM.
        okd = valid & np.isfinite(dem)
        a, b = np.polyfit(rel[okd], dem[okd], 1)
        product_affine = a * rel + b
        products = {
            "copernicus": dem,
            "fusion": product_fusion,
            "affine": product_affine,
            "fusion_oracle": product_oracle,
        }
        for name, pred in products.items():
            row = {
                "site": site_id,
                "landscape": landscape,
                "gsd_m": gsd,
                "product": name,
                "tiled": tiled,
                "detail_scale": s_fit
                if name == "fusion"
                else (s_oracle if name == "fusion_oracle" else None),
                "inference_s": round(infer_s, 1),
                "vs_lidar": _metrics(pred, truth),
                "vs_lidar_30m": _metrics(_block(pred, k), _block(truth, k)),
                "vs_copernicus": _metrics(pred, dem),
            }
            rows.append(row)
            print(json.dumps(row), flush=True)
    return rows


def _align_bilinear(path: Path, transform, crs, shape: tuple[int, int]) -> np.ndarray:  # type: ignore[no-untyped-def]
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import reproject

    out = np.full(shape, np.nan, dtype=np.float64)
    with rasterio.open(path) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=out,
            dst_transform=transform,
            dst_crs=crs,
            dst_nodata=np.nan,
            resampling=Resampling.bilinear,
        )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/benchmarks/swiss")
    parser.add_argument("--gsd", type=float, nargs="+", default=[0.6, 2.0])
    parser.add_argument("--sites", nargs="*", default=None)
    parser.add_argument("--tiled", action="store_true")
    args = parser.parse_args(argv)
    out = Path(args.out)
    chosen = [s for s in SITES if not args.sites or s[0] in args.sites]
    rows = []
    for site in chosen:
        try:
            rows.extend(run_site(site, out, args.gsd, args.tiled))
        except Exception as exc:  # keep going; record the failure
            print(
                json.dumps({"site": site[0], "error": f"{type(exc).__name__}: {exc}"}), flush=True
            )
    suffix = "tiled" if args.tiled else "single"
    (out / f"results_{suffix}.json").write_text(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
