#!/usr/bin/env python3
"""Backend execution bridge: TypeScript → Python → backend products → JSON.

This script executes the ACTUAL depthwizard backend subsystems and outputs
serialized products as JSON to stdout.

Architecture:
  TypeScript (bridge.ts)
    → spawns this Python script
    → this script runs real backend code (no reimplementation)
    → outputs JSON to stdout
    → TypeScript parses, validates, adapts

Modes:
  python scripts/backend_bridge.py <input_image_path>
      DepthResult for a real input file.
  python scripts/backend_bridge.py --synthetic <width> <height>
      DepthResult for a generated synthetic input (depth-only path).
  python scripts/backend_bridge.py --terrain <width> <height>
      Full terrain chain for a generated synthetic input:
        synthetic input
        → SyntheticDepthBackend.estimate_depth()
        → deterministic dev calibration (scale_offset)
        → create_scientific_height_product()
        → rasterize_height_product()  (DSMGrid)
        → build_terrain_mesh()        (TerrainMesh)
      Outputs depth_result + dsm + mesh. All values are produced by the
      real backend subsystems; this script only orchestrates and serializes.

IMPORTANT: This script requires the depthwizard package to be installed.
It does NOT contain a duplicate implementation of any backend behavior.
The dev calibration mirrors tests/height/support.py::exact_calibration
(the sanctioned deterministic dev calibration); the fit itself is computed
by the real ScaleOffsetCalibrator.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Dynamic sys.path resolution for depthwizard package
# ---------------------------------------------------------------------------

_script_dir = Path(__file__).resolve().parent
for _candidate in (
    _script_dir.parent / "src",
    _script_dir / "src",
    _script_dir.parent,
    _script_dir,
):
    if (_candidate / "depthwizard").is_dir() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))

# ---------------------------------------------------------------------------
# Import the ACTUAL depthwizard backend — no fallback, no duplicate formulas.
# Serialization uses the canonical depthwizard.integration layer, never a
# bridge-owned copy of the wire shape.
# ---------------------------------------------------------------------------

try:
    from depthwizard.backends.synthetic import SyntheticDepthBackend
    from depthwizard.calibration import (
        CalibrationSamples,
        ScaleOffsetCalibrator,
    )
    from depthwizard.contracts.semantics import ElevationSemantics
    from depthwizard.dsm.rasterize import rasterize_height_product
    from depthwizard.height import create_scientific_height_product
    from depthwizard.ingestion.api import inspect_input
    from depthwizard.integration import terrain_product, to_json_text
    from depthwizard.mesh.build import build_terrain_mesh
except ImportError as exc:
    print(
        json.dumps(
            {
                "error": (
                    "depthwizard package not installed. "
                    "Install it with: pip install -e .  "
                    f"Original error: {exc}"
                ),
                "type": "ImportError",
            }
        )
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Backend selection (no silent fallback: unknown/unavailable backends fail
# loudly with a JSON error and a non-zero exit).
# ---------------------------------------------------------------------------

SYNTHETIC_BACKEND_NAME = "synthetic-depth"
DAV2_BACKEND_NAME = "depth-anything-v2-small"

DEV_REFERENCE_ID = "synthetic-dev-ref"
DEV_TARGET_SEMANTICS = ElevationSemantics.ABSOLUTE_ELEVATION_DSM


def resolve_backend(name: str, device: str | None = None) -> Any:
    """Build the requested backend or raise a descriptive error.

    The deterministic synthetic backend is always available. The real
    DA-V2 backend requires its runtime (upstream source + torch) and an
    external checkpoint (``DW_DAV2_CKPT`` or ``checkpoints/``); anything
    missing raises instead of substituting synthetic output.
    """
    if name == SYNTHETIC_BACKEND_NAME:
        return SyntheticDepthBackend()
    if name == DAV2_BACKEND_NAME:
        try:
            from depthwizard.backends.depth_anything_v2 import DepthAnythingV2Backend
        except ImportError as exc:
            raise RuntimeError(
                f"backend {name!r} unavailable: DA-V2 runtime not importable ({exc}). "
                "Install the 'dav2' extra and provide the upstream source."
            ) from exc
        checkpoint = os.environ.get("DW_DAV2_CKPT")
        backend_device = device or os.environ.get("DW_DAV2_DEVICE", "cpu")
        try:
            return DepthAnythingV2Backend(
                checkpoint=Path(checkpoint) if checkpoint else None,
                device=backend_device,  # type: ignore[arg-type]
            )
        except Exception as exc:
            raise RuntimeError(
                f"backend {name!r} unavailable: {exc}. "
                "Set DW_DAV2_CKPT to an external checkpoint; weights are never committed."
            ) from exc
    raise ValueError(
        f"unknown backend {name!r} (supported: {SYNTHETIC_BACKEND_NAME}, {DAV2_BACKEND_NAME})"
    )


def fit_dev_calibration(depth: Any, target: ElevationSemantics) -> Any:
    """Fit the sanctioned deterministic dev calibration to actual values.

    Reference rule ``reference = 2.5 * predicted + 10`` (same as
    ``tests/pipeline/support.py::SyntheticCalibrationProvider``) fitted
    with the real ``ScaleOffsetCalibrator`` against the backend's actual
    depth output. Never production data; the reference id says so.
    """
    predicted = depth.depth_values
    samples = CalibrationSamples(
        predicted_values=predicted,
        reference_values=tuple(2.5 * value + 10.0 for value in predicted),
        reference_id=DEV_REFERENCE_ID,
        reference_units="meters",
        target_semantics=target,
        source_checksum=depth.provenance.input_checksum,
    )
    return ScaleOffsetCalibrator().calibrate(samples)


def create_synthetic_png(width: int, height: int, path: Path) -> Path:
    """Create a deterministic synthetic PNG for testing using Pillow."""
    from PIL import Image

    img = Image.new("RGB", (width, height))
    pixels = img.load()
    assert pixels is not None
    for row in range(height):
        for col in range(width):
            v = 255 if (row + col) % 2 == 0 else 0
            pixels[col, row] = (v, (col * 32) % 256, (row * 40) % 256)
    img.save(path, format="PNG")
    return path


def emit_stage(name: str) -> None:
    """Report a genuinely completed backend stage (stderr, never stdout).

    Consumers parse lines starting with ``STAGE ``. A line is emitted
    only after the corresponding backend stage has actually finished —
    never speculatively, never on a timer.
    """
    print(f"STAGE {name}", file=sys.stderr, flush=True)


def run_depth_only(
    width: int, height: int, backend_name: str = SYNTHETIC_BACKEND_NAME
) -> dict[str, Any]:
    """Depth-only path: synthetic input → DepthResult."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        create_synthetic_png(width, height, tmp_path)
        inspection = inspect_input(tmp_path)
        emit_stage("preprocessing")
        result = resolve_backend(backend_name).estimate_depth(inspection)
        emit_stage("inference_running")
        return dict(result.model_dump())
    finally:
        tmp_path.unlink(missing_ok=True)


def run_terrain(
    width: int, height: int, backend_name: str = SYNTHETIC_BACKEND_NAME
) -> dict[str, Any]:
    """Full terrain chain on a generated synthetic input."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        create_synthetic_png(width, height, tmp_path)
        return run_terrain_on_path(tmp_path, backend_name=backend_name)
    finally:
        tmp_path.unlink(missing_ok=True)


METRIC_TARGETS = ("height_agl_ndsm", "absolute_elevation_dsm")

_USAGE = (
    "Usage: backend_bridge.py [--backend <name>] [--device <device>] [--mode metric|relative] "
    "<input_path> | --synthetic <w> <h> "
    "| --terrain <w> <h> | --terrain-file <path> [target] "
    "| --inspect <path> | --capabilities"
)


def parse_target_semantics(value: str | None) -> ElevationSemantics:
    """Resolve a caller-requested metric target against backend semantics."""
    if value is None:
        return DEV_TARGET_SEMANTICS
    try:
        target = ElevationSemantics(value)
    except ValueError:
        raise ValueError(
            f"unsupported target semantics: {value!r} (supported: {', '.join(METRIC_TARGETS)})"
        ) from None
    if target.value not in METRIC_TARGETS:
        raise ValueError(
            f"target semantics must be metric, got {value!r} "
            f"(supported: {', '.join(METRIC_TARGETS)})"
        )
    return target


def run_terrain_on_path(
    input_path: Path,
    target_value: str | None = None,
    backend_name: str = SYNTHETIC_BACKEND_NAME,
    device: str | None = None,
) -> dict[str, Any]:
    """Full terrain chain on a real input file using only real backend subsystems."""
    target = parse_target_semantics(target_value)
    inspection = inspect_input(input_path)
    emit_stage("preprocessing")
    backend = resolve_backend(backend_name, device)
    if hasattr(backend, "load"):
        backend.load()
    try:
        depth = backend.estimate_depth(inspection)
    finally:
        close = getattr(backend, "close", None)
        if callable(close):
            close()
    emit_stage("inference_running")

    calibration = fit_dev_calibration(depth, target)

    emit_stage("calibrating")
    product = create_scientific_height_product(depth, calibration, target)
    grid = rasterize_height_product(product)
    emit_stage("dsm_generation")
    mesh = build_terrain_mesh(grid)
    emit_stage("mesh_generation")

    # Canonical serialization only: the transport shape is owned by
    # depthwizard.integration, never reconstructed here. The stages list
    # records the stages this script genuinely executed, in order.
    payload: dict[str, Any] = json.loads(to_json_text(terrain_product(depth, grid, mesh)))
    payload["stages"] = [
        "preprocessing",
        "inference_running",
        "calibrating",
        "dsm_generation",
        "mesh_generation",
    ]
    return payload


def run_relative_on_path(
    input_path: Path,
    backend_name: str = SYNTHETIC_BACKEND_NAME,
    device: str | None = None,
) -> dict[str, Any]:
    """Relative terrain chain on a real input file (no calibration, ever)."""
    from depthwizard.integration import relative_product, to_json_text
    from depthwizard.rdsm.mesh import build_relative_mesh
    from depthwizard.rdsm.rasterize import rasterize_relative_surface

    inspection = inspect_input(input_path)
    emit_stage("preprocessing")
    backend = resolve_backend(backend_name, device)
    if hasattr(backend, "load"):
        backend.load()
    try:
        depth = backend.estimate_depth(inspection)
    finally:
        close = getattr(backend, "close", None)
        if callable(close):
            close()
    emit_stage("inference_running")
    grid = rasterize_relative_surface(depth)
    emit_stage("rsm_generation")
    mesh = build_relative_mesh(grid)
    emit_stage("mesh_generation")

    payload: dict[str, Any] = json.loads(to_json_text(relative_product(depth, grid, mesh)))
    payload["stages"] = [
        "preprocessing",
        "inference_running",
        "rsm_generation",
        "mesh_generation",
    ]
    return payload


def run_capabilities() -> dict[str, Any]:
    """Report actual backend input capabilities (no input needed)."""
    from depthwizard.ingestion.formats import SUPPORTED_SUFFIXES

    return {
        "contract_version": "1",
        "supported_suffixes": list(SUPPORTED_SUFFIXES),
    }


def run_inspect(input_path: Path) -> dict[str, Any]:
    """Validate one real input file with the actual backend ingestion."""
    from depthwizard.errors import DepthWizardError

    if not input_path.exists():
        return {
            "valid": False,
            "failure": {
                "code": "invalid_input",
                "message": f"Input file not found: {input_path.name}",
            },
        }
    try:
        inspection = inspect_input(input_path)
        return {"valid": True, "inspection": inspection.model_dump(mode="json")}
    except DepthWizardError as exc:
        return {
            "valid": False,
            "failure": {"code": exc.code, "message": str(exc)},
        }
    except ImportError as exc:
        return {
            "valid": False,
            "failure": {
                "code": "environment_unsupported",
                "message": f"Backend reader unavailable in this environment: {exc}",
            },
        }


def main() -> None:
    """Main entry point: invoke the actual backend and serialize the result."""
    if len(sys.argv) < 2:
        print(json.dumps({"error": _USAGE}))
        sys.exit(1)

    args = sys.argv[1:]
    backend_name = SYNTHETIC_BACKEND_NAME
    device: str | None = None
    mode = "metric"
    positional: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--backend" and i + 1 < len(args):
            backend_name = args[i + 1]
            i += 2
        elif args[i] == "--device" and i + 1 < len(args):
            device = args[i + 1]
            i += 2
        elif args[i] == "--mode" and i + 1 < len(args):
            mode = args[i + 1]
            i += 2
        else:
            positional.append(args[i])
            i += 1
    if mode not in ("metric", "relative"):
        print(json.dumps({"error": f"Unknown mode {mode!r} (expected 'metric' or 'relative')"}))
        sys.exit(1)

    try:
        if not positional:
            print(json.dumps({"error": _USAGE}))
            sys.exit(1)
        if positional[0] == "--terrain":
            width = int(positional[1]) if len(positional) > 1 else 8
            height = int(positional[2]) if len(positional) > 2 else 8
            print(
                json.dumps(
                    run_terrain(width, height, backend_name=backend_name),
                    allow_nan=False,
                )
            )
        elif positional[0] == "--terrain-file":
            if len(positional) < 2:
                print(json.dumps({"error": "Missing input path for --terrain-file"}))
                sys.exit(1)
            input_path = Path(positional[1])
            if not input_path.exists():
                print(json.dumps({"error": f"Input file not found: {input_path}"}))
                sys.exit(1)
            target_value = positional[2] if len(positional) > 2 else None
            if mode == "relative":
                runner = run_relative_on_path(
                    input_path,
                    backend_name=backend_name,
                    device=device,
                )
            else:
                runner = run_terrain_on_path(
                    input_path,
                    target_value,
                    backend_name=backend_name,
                    device=device,
                )
            print(json.dumps(runner, allow_nan=False))
        elif positional[0] == "--inspect":
            if len(positional) < 2:
                print(json.dumps({"error": "Missing input path for --inspect"}))
                sys.exit(1)
            print(json.dumps(run_inspect(Path(positional[1]))))
        elif positional[0] == "--capabilities":
            print(json.dumps(run_capabilities()))
        elif positional[0] == "--synthetic":
            width = int(positional[1]) if len(positional) > 1 else 8
            height = int(positional[2]) if len(positional) > 2 else 8
            print(json.dumps(run_depth_only(width, height, backend_name=backend_name)))
        else:
            input_path = Path(positional[0])
            if not input_path.exists():
                print(json.dumps({"error": f"Input file not found: {input_path}"}))
                sys.exit(1)

            inspection = inspect_input(input_path)
            result = resolve_backend(backend_name).estimate_depth(inspection)
            print(json.dumps(result.model_dump()))

    except Exception as e:
        print(json.dumps({"error": str(e), "type": type(e).__name__}))
        sys.exit(1)


if __name__ == "__main__":
    main()
