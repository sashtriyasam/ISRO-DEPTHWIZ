#!/usr/bin/env python3
"""Level-3 system evidence harness: real DA-V2 across representative images.

This script executes the ACTUAL DepthWizard subsystems and emits a JSON
evidence record to stdout (or --out <path>). It implements no science;
it only orchestrates real entry points and serializes observations.

Fixture generation (deterministic, reproducible without network):
  seed = 26175 (numpy Generator(PCG64))
  base = horizontal gradient + vertical gradient (0..255)
  texture = 40*sin(2*pi*x/24) + 30*cos(2*pi*y/19)
  shapes = one bright rectangle + one dark filled circle (positions scale
           with dimensions), clipped to 0..255, saved as PNG (cv2, uint8 BGR)
  Any engineer can regenerate byte-identical fixtures by running this
  script: fixtures are written under --fixture-dir (default: system temp).

Matrix (all PNG, 3-channel RGB):
  small  32x32, medium 64x64, photo-small 160x120, photo 320x240.

For each case the harness records: input dims/type, backend, device,
model load time (once per process), per-run inference time (2 runs),
output dims, finite status, depth semantics, and repeatability
(byte-identical second run or not).

Full pipeline (64x64): inspect -> DepthAnythingV2Backend -> DepthResult
-> ScaleOffsetCalibrator (deterministic dev rule reference = 2.5*pred+10,
same rule as tests/pipeline/support.py) -> height product -> DSM -> mesh,
plus LocalService backend selection, PipelineRunner to COMPLETED, and
integration-adapter JSON transport round-trip.

Timings are single-session engineering observations, NOT benchmarks.

Usage:
  set PYTHONPATH to include the pinned upstream DA-V2 source, e.g.
    $env:PYTHONPATH="<dav2-clone>"
  python scripts/dav2_level3_evidence.py [--out evidence.json]
      [--fixture-dir <dir>] [--checkpoint <path>] [--device cpu]

  Environment overrides: DW_DAV2_CKPT, DW_DAV2_DEVICE (default cpu).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import tempfile
import time
from pathlib import Path

FIXTURE_SEED = 26175
MATRIX: list[tuple[str, int, int]] = [
    ("small-32x32", 32, 32),
    ("medium-64x64", 64, 64),
    ("photo-small-160x120", 160, 120),
    ("photo-320x240", 320, 240),
]
PIPELINE_CASE = ("medium-64x64", 64, 64)


def make_fixture(path: Path, width: int, height: int) -> dict:
    """Write a deterministic photographic-like PNG fixture; return identity."""
    import numpy as np

    rng = np.random.default_rng(FIXTURE_SEED)
    yy, xx = np.mgrid[0:height, 0:width].astype(float)
    base = (xx / max(width - 1, 1) * 140.0) + (yy / max(height - 1, 1) * 80.0)
    texture = 40.0 * np.sin(2 * math.pi * xx / 24.0) + 30.0 * np.cos(2 * math.pi * yy / 19.0)
    img = base + texture
    # bright rectangle, dark circle; positions scale with dimensions
    x0, y0 = int(width * 0.15), int(height * 0.2)
    x1, y1 = int(width * 0.55), int(height * 0.7)
    img[y0:y1, x0:x1] += 60.0
    cx, cy, r = int(width * 0.72), int(height * 0.6), int(min(width, height) * 0.14)
    mask = (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r
    img[mask] -= 90.0
    img = np.clip(img + rng.normal(0, 2.0, img.shape), 0, 255).astype(np.uint8)
    bgr = np.stack([img, img, img], axis=-1)

    import cv2

    ok = cv2.imwrite(str(path), bgr)
    if not ok:
        raise RuntimeError(f"failed to write fixture {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": path.name,
        "seed": FIXTURE_SEED,
        "sha256": digest,
        "bytes": path.stat().st_size,
    }


def sha256_file(path: Path) -> str:
    """Stream a file's SHA-256."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> str | None:
    """Repository HEAD SHA, if git is available."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except Exception:
        return None


def main() -> int:
    """Run the evidence matrix and emit the JSON record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None, help="write JSON record to path")
    parser.add_argument("--fixture-dir", default=None, help="fixture directory")
    parser.add_argument("--checkpoint", default=None, help="DA-V2 checkpoint path")
    parser.add_argument("--device", default=None, help="torch device (default cpu)")
    args = parser.parse_args()

    ckpt = Path(
        args.checkpoint or os.environ.get("DW_DAV2_CKPT", "checkpoints/depth_anything_v2_vits.pth")
    )
    device = args.device or os.environ.get("DW_DAV2_DEVICE", "cpu")
    fixture_dir = (
        Path(args.fixture_dir) if args.fixture_dir else Path(tempfile.mkdtemp(prefix="dw-l3-"))
    )
    fixture_dir.mkdir(parents=True, exist_ok=True)

    from depthwizard.backends.depth_anything_v2 import (
        CHECKPOINT_SHA256,
        UPSTREAM_REVISION,
        DepthAnythingV2Backend,
    )
    from depthwizard.ingestion import inspect_input

    record: dict = {
        "kind": "dav2-level3-evidence",
        "note": "engineering observations, NOT benchmarks",
        "repository_sha": git_sha(),
        "os": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "device": device,
        "upstream_revision": UPSTREAM_REVISION,
        "checkpoint": {
            "path": ckpt.as_posix(),
            "present": ckpt.is_file(),
            "sha256": sha256_file(ckpt) if ckpt.is_file() else None,
            "matches_code": (sha256_file(ckpt) == CHECKPOINT_SHA256) if ckpt.is_file() else False,
            "code_sha256": CHECKPOINT_SHA256,
        },
    }
    try:
        import torch
        import torchvision  # noqa: F401

        record["torch"] = getattr(torch, "__version__", "unknown")
        try:
            import torchvision as _tv

            record["torchvision"] = getattr(_tv, "__version__", "unknown")
        except Exception:
            record["torchvision"] = "unknown"
    except Exception as e:
        record["torch"] = f"unavailable: {e}"
        record["torchvision"] = "unavailable"
    try:
        import cv2

        record["opencv"] = getattr(cv2, "__version__", "unknown")
    except Exception as e:
        record["opencv"] = f"unavailable: {e}"
    try:
        import depth_anything_v2  # noqa: F401

        # Upstream clone is a namespace package (no __init__.py): use __path__.
        search = list(getattr(depth_anything_v2, "__path__", []))
        record["dav2_runtime"] = search[0] if search else "importable"
    except Exception as e:
        record["dav2_runtime"] = f"unavailable: {e}"

    if not ckpt.is_file():
        record["error"] = f"checkpoint not found: {ckpt}"
        text = json.dumps(record, indent=2)
        print(text)
        if args.out:
            Path(args.out).write_text(text, encoding="utf-8")
        return 2

    backend = DepthAnythingV2Backend(checkpoint=ckpt, device=device)  # type: ignore[arg-type]
    t0 = time.perf_counter()
    backend.load()
    record["model_load_s"] = round(time.perf_counter() - t0, 3)

    cases = []
    inspections = {}
    results = {}
    for name, width, height in MATRIX:
        fpath = fixture_dir / f"dw-l3-{name}.png"
        identity = make_fixture(fpath, width, height)
        inspection = inspect_input(str(fpath))
        inspections[name] = inspection
        t0 = time.perf_counter()
        first = backend.estimate_depth(inspection)
        infer1 = round(time.perf_counter() - t0, 3)
        t0 = time.perf_counter()
        second = backend.estimate_depth(inspection)
        infer2 = round(time.perf_counter() - t0, 3)
        results[name] = second
        cases.append(
            {
                "name": name,
                "input": {"width": width, "height": height, "type": "PNG 3-channel uint8"},
                "fixture": identity,
                "backend": first.model_name,
                "device": device,
                "inference_s_run1": infer1,
                "inference_s_run2": infer2,
                "output": {
                    "width": first.output_resolution.width,
                    "height": first.output_resolution.height,
                    "count": len(first.depth_values),
                },
                "finite": all(math.isfinite(v) for v in first.depth_values),
                "depth_scale": first.depth_scale.value,
                "units": first.units,
                "elevation_semantics": first.elevation_semantics.value,
                "georeferencing": first.georeferencing.value,
                "deterministic_repeat": list(first.depth_values) == list(second.depth_values),
                "value_min": round(min(first.depth_values), 4),
                "value_max": round(max(first.depth_values), 4),
            }
        )
    backend.close()
    record["cases"] = cases

    # Full canonical pipeline on the medium case (real entry points only).
    from depthwizard.calibration import CalibrationSamples, ScaleOffsetCalibrator
    from depthwizard.contracts.semantics import ElevationSemantics
    from depthwizard.dsm.rasterize import rasterize_height_product
    from depthwizard.height.factory import create_scientific_height_product
    from depthwizard.integration.adapt import depth_to_transport
    from depthwizard.integration.wire import to_json_text
    from depthwizard.mesh.build import build_terrain_mesh
    from depthwizard.pipeline import PipelineRequest, PipelineRunner
    from depthwizard.service.service import LocalService

    pname, _, _ = PIPELINE_CASE
    depth = results[pname]
    inspection = inspections[pname]
    t0 = time.perf_counter()
    samples = CalibrationSamples(
        predicted_values=depth.depth_values,
        reference_values=tuple(2.5 * v + 10.0 for v in depth.depth_values),
        reference_id="level3-evidence-ref",
        reference_units="meters",
        target_semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
        source_checksum=depth.provenance.input_checksum,
    )
    calibration = ScaleOffsetCalibrator().calibrate(samples)
    product = create_scientific_height_product(
        depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM
    )
    dsm = rasterize_height_product(product)
    mesh = build_terrain_mesh(dsm)
    pipeline_direct_s = round(time.perf_counter() - t0, 3)

    class _EvidenceProvider:
        name = "level3-evidence-provider"

        def calibrate(self, depth_result):  # type: ignore[no-untyped-def]
            """Deterministic dev rule (same as tests/pipeline/support.py)."""
            s = CalibrationSamples(
                predicted_values=depth_result.depth_values,
                reference_values=tuple(2.5 * v + 10.0 for v in depth_result.depth_values),
                reference_id="level3-evidence-ref",
                reference_units="meters",
                target_semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
                source_checksum=depth_result.provenance.input_checksum,
            )
            return ScaleOffsetCalibrator().calibrate(s)

    runner_request = PipelineRequest(
        input_path=str(fixture_dir / f"dw-l3-{pname}.png"),
        backend=DepthAnythingV2Backend(checkpoint=ckpt, device=device),  # type: ignore[arg-type]
        calibration_provider=_EvidenceProvider(),
        target_semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
        build_mesh=True,
    )
    run = PipelineRunner().run(runner_request)
    service = LocalService(
        backends={
            "depth-anything-v2-small": DepthAnythingV2Backend(checkpoint=ckpt, device=device),  # type: ignore[arg-type]
        }
    )
    transport_text = to_json_text(depth_to_transport(depth))
    transport = json.loads(transport_text)
    record["pipeline"] = {
        "case": pname,
        "direct_stages_s": pipeline_direct_s,
        "height_units": product.units,
        "height_semantics": product.semantics.value,
        "relative_vs_metric_boundary": (
            f"depth {depth.depth_scale.value}/units None -> "
            f"height {product.units}/{product.semantics.value}"
        ),
        "dsm": {
            "width": dsm.width,
            "height": dsm.height,
            "units": dsm.units,
            "semantics": dsm.semantics.value,
        },
        "mesh": {"vertices": mesh.vertex_count, "triangles": mesh.triangle_count},
        "runner_states": [s.value for s in run.states],
        "runner_mesh": run.mesh is not None,
        "service_backends": sorted(service.capabilities().available_backends),
        "transport": {
            "depth_scale": transport["depth_scale"],
            "units": transport.get("units"),
            "model": transport["model_name"],
            "values": len(transport["depth_values"]),
            "provenance_model": transport["provenance"]["model_name"],
        },
    }

    text = json.dumps(record, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
