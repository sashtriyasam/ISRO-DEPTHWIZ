#!/usr/bin/env python3
"""Canonical evaluation runner: manifest → inference → calibration → metrics.

Reads a dataset manifest (relative paths + checksums, no absolute
developer paths), runs the canonical pipeline per sample with the
requested backend, fits calibration on deterministic control pixels,
scores held-out pixels, and writes a machine-readable
``EvaluationRun`` JSON document (summaries only, never prediction
dumps).

Nothing here downloads datasets, checkpoints, or code. Missing local
assets fail with structured ``DATASET_*``/``BACKEND_*`` errors before
any misleading partial result is produced.

Usage:
  python scripts/evaluate.py --dataset gamus --manifest manifests/gamus.json
      --split test --backend depth-anything-v2-small
      --gamus-root <dir> --stride 8 --output results.json [--report report.md]
  python scripts/evaluate.py --smoke [--output results.json]

Environment: DW_DAV2_CKPT (+ upstream source on PYTHONPATH) for real
DA-V2; DW_EVAL_DEVICE (default cpu).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


def _manifest_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fail(code: str, message: str) -> int:
    print(json.dumps({"ok": False, "code": code, "message": message}))
    return 1


def _run_smoke(output: Path | None) -> int:
    from depthwizard.evaluation.smoke import run_smoke

    result, _, _ = run_smoke()
    document = result.model_dump(mode="json")
    text = json.dumps(document, indent=2)
    if output is not None:
        output.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


def _resolve_backend(name: str, device: str) -> object:
    from depthwizard.backends.synthetic import SyntheticDepthBackend

    if name == "synthetic-depth":
        return SyntheticDepthBackend()
    if name == "depth-anything-v2-small":
        try:
            from depthwizard.backends.depth_anything_v2 import DepthAnythingV2Backend
        except ImportError as exc:
            raise RuntimeError(
                "BACKEND_UNAVAILABLE: DA-V2 runtime not importable. "
                f"Install the 'dav2' extra. ({exc})"
            ) from exc
        checkpoint = os.environ.get("DW_DAV2_CKPT")
        backend = DepthAnythingV2Backend(
            checkpoint=Path(checkpoint) if checkpoint else None,
            device=device,  # type: ignore[arg-type]
        )
        backend.load()
        return backend
    raise ValueError(
        f"unknown backend {name!r} (expected synthetic-depth or depth-anything-v2-small)"
    )


def _load_manifest(path: Path) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"DATASET_MANIFEST_INVALID: {path.name}: {exc}") from exc
    if not isinstance(document, dict) or "samples" not in document:
        raise ValueError(f"DATASET_MANIFEST_INVALID: {path.name} lacks a 'samples' list")
    return document


def main(argv: list[str] | None = None) -> int:
    """Validate inputs, run the evaluation, write the result document."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="gamus")
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--split", default="test")
    parser.add_argument("--backend", default="depth-anything-v2-small")
    parser.add_argument("--gamus-root", default=None)
    parser.add_argument("--stride", type=int, default=8)
    parser.add_argument("--target", default="height_agl_ndsm")
    parser.add_argument("--output", default=None)
    parser.add_argument("--report", default=None)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)

    if args.smoke:
        return _run_smoke(Path(args.output) if args.output else None)
    if args.manifest is None:
        return _fail("DATASET_MISSING", "no --manifest provided and --smoke not set")

    from depthwizard.contracts.semantics import ElevationSemantics
    from depthwizard.evaluation.datasets import EvaluationSample, GamusDataset
    from depthwizard.evaluation.runner import evaluate_run, run_sample

    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        return _fail("DATASET_MANIFEST_INVALID", f"manifest not found: {manifest_path}")
    try:
        document = _load_manifest(manifest_path)
    except ValueError as exc:
        return _fail("DATASET_MANIFEST_INVALID", str(exc))
    if document.get("dataset") != args.dataset:
        return _fail(
            "DATASET_MANIFEST_INVALID",
            f"manifest dataset {document.get('dataset')!r} != {args.dataset!r}",
        )
    try:
        target = ElevationSemantics(args.target)
    except ValueError:
        return _fail("UNSUPPORTED_SEMANTICS", f"unknown target semantics: {args.target!r}")

    root_value = args.gamus_root or os.environ.get("GAMUS_ROOT")
    if root_value is None:
        return _fail("DATASET_MISSING", "GAMUS root unknown: pass --gamus-root or set GAMUS_ROOT")
    root = Path(root_value)
    samples = []
    for entry in document["samples"]:
        try:
            candidate = EvaluationSample(**entry)
        except Exception as exc:
            return _fail("DATASET_MANIFEST_INVALID", f"bad sample entry: {exc}")
        if candidate.split == args.split:
            samples.append(candidate)
    if not samples:
        return _fail("DATASET_MISSING", f"no '{args.split}' samples in manifest")

    dataset = GamusDataset(root, args.split, manifest=samples)
    manifest_checksum = _manifest_checksum(manifest_path)
    device = os.environ.get("DW_EVAL_DEVICE", "cpu")
    try:
        backend = _resolve_backend(args.backend, device)
    except (RuntimeError, ValueError) as exc:
        return _fail("BACKEND_UNAVAILABLE", str(exc))
    try:
        results, pairs = [], []
        for sample in dataset.list_samples():
            loaded = dataset.load_sample(sample)
            result, calibrated, reference = run_sample(
                loaded,
                backend,
                target=target,
                stride=args.stride,
                dataset_release=document.get("release"),
                manifest_checksum=manifest_checksum,
                device=device,
            )
            results.append(result)
            pairs.append((calibrated, reference))
        run = evaluate_run(
            results,
            pairs,
            dataset_release=document.get("release"),
            manifest_checksum=manifest_checksum,
            device=device,
        )
    except FileNotFoundError as exc:
        return _fail("REFERENCE_MISSING", str(exc))
    except ValueError as exc:
        message = str(exc)
        code = message.split(":")[0] if ":" in message else "EVALUATION_FAILED"
        return _fail(code, message)
    finally:
        close = getattr(backend, "close", None)
        if callable(close):
            close()

    if args.backend == "depth-anything-v2-small":
        try:
            from depthwizard.backends.depth_anything_v2 import (
                CHECKPOINT_SHA256,
                UPSTREAM_REVISION,
            )

            run = run.model_copy(
                update={
                    "checkpoint_sha256": CHECKPOINT_SHA256,
                    "upstream_revision": UPSTREAM_REVISION,
                }
            )
            per_sample = tuple(
                result.model_copy(
                    update={
                        "checkpoint_sha256": CHECKPOINT_SHA256,
                        "upstream_revision": UPSTREAM_REVISION,
                    }
                )
                for result in run.per_sample
            )
            run = run.model_copy(update={"per_sample": per_sample})
        except ImportError:
            pass

    text = run.model_dump_json(indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    if args.report:
        lines = [
            f"# Evaluation report: {run.dataset_name} / {run.split}",
            "",
            f"samples: {run.sample_count}, valid pixels: {run.valid_pixels}, "
            f"coverage: {run.coverage_fraction:.4f}",
            f"pooled MAE: {run.pooled_mae:.4f} m, RMSE: {run.pooled_rmse:.4f} m, "
            f"R²: {run.pooled_r_squared:.4f}",
            f"model: {run.model_name}, calibration: {run.calibration_protocol}, "
            f"alignment: {run.alignment_protocol}",
        ]
        Path(args.report).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
