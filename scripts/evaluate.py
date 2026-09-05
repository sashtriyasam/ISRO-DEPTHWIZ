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
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--sample-offset", type=int, default=0)
    parser.add_argument("--resume-dir", default=None)
    parser.add_argument("--non-strict", action="store_true")
    parser.add_argument("--output", default=None)
    parser.add_argument("--report", default=None)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)

    if args.smoke:
        return _run_smoke(Path(args.output) if args.output else None)
    if args.manifest is None:
        return _fail("DATASET_MISSING", "no --manifest provided and --smoke not set")

    import time

    from depthwizard.contracts.semantics import ElevationSemantics
    from depthwizard.evaluation.datasets import EvaluationSample, GamusDataset, sha256_file
    from depthwizard.evaluation.metrics import PooledAccumulator
    from depthwizard.evaluation.resume import (
        load_resume_records,
        restore_accumulator,
        run_identity,
        save_record,
        snapshot_accumulator,
    )
    from depthwizard.evaluation.runner import evaluate_run, run_sample, select_samples

    def _record_failure(
        failures: list[dict[str, str]], sample_id: str, code: str, message: str
    ) -> None:
        failures.append({"sample_id": sample_id, "code": code, "message": message[:300]})

    def _verify_sample_checksums(sample: EvaluationSample) -> None:
        for kind, relpath, expected in (
            ("image", sample.image_path, sample.input_checksum),
            ("reference", sample.reference_path, sample.reference_checksum),
        ):
            if expected is None:
                continue
            actual_file = root / relpath
            if not actual_file.is_file():
                raise FileNotFoundError(f"{kind} missing: {sample.sample_id}")
            if sha256_file(actual_file) != expected:
                raise ValueError(
                    f"DATASET_MANIFEST_INVALID: {kind} checksum mismatch for {sample.sample_id}"
                )

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
        selected = select_samples(samples, args.max_samples, args.sample_offset)
    except ValueError as exc:
        return _fail("DATASET_MANIFEST_INVALID", str(exc))
    if not selected:
        return _fail("DATASET_MISSING", "selection is empty (offset beyond manifest?)")
    model_load_start = time.perf_counter()
    try:
        backend = _resolve_backend(args.backend, device)
    except (RuntimeError, ValueError) as exc:
        return _fail("BACKEND_UNAVAILABLE", str(exc))
    model_load_seconds = round(time.perf_counter() - model_load_start, 3)
    checkpoint_sha256: str | None = None
    upstream_revision: str | None = None
    if args.backend == "depth-anything-v2-small":
        try:
            from depthwizard.backends.depth_anything_v2 import (
                CHECKPOINT_SHA256,
                UPSTREAM_REVISION,
            )

            checkpoint_sha256, upstream_revision = CHECKPOINT_SHA256, UPSTREAM_REVISION
        except ImportError:
            pass
    repository_sha: str | None = None
    try:
        import subprocess as _subprocess

        proc = _subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30
        )
        if proc.returncode == 0 and proc.stdout.strip():
            repository_sha = proc.stdout.strip()
    except Exception:
        repository_sha = None
    identity = run_identity(
        manifest_checksum,
        args.backend,
        checkpoint_sha256,
        "control-stride",
        "native-pixel",
        repository_sha,
        args.dataset,
        args.split,
        args.stride,
        args.target,
    )
    resume_dir = Path(args.resume_dir) if args.resume_dir else None
    resumed = (
        load_resume_records(resume_dir, [sample.sample_id for sample in selected], identity)
        if resume_dir
        else {}
    )
    try:
        results: list = []
        failures: list[dict[str, str]] = []
        accumulator = PooledAccumulator()
        city_accumulators: dict[str, PooledAccumulator] = {}
        run_start = time.perf_counter()
        for sample in selected:
            resumed_record = resumed.get(sample.sample_id)
            if resumed_record is not None:
                result, snapshot = resumed_record
                result = result.model_copy(
                    update={
                        "checkpoint_sha256": checkpoint_sha256 or result.checkpoint_sha256,
                        "upstream_revision": upstream_revision or result.upstream_revision,
                        "repository_sha": repository_sha or result.repository_sha,
                    }
                )
                results.append(result)
                restore_accumulator(accumulator, snapshot)
                city = sample.source.get("city")
                if city:
                    restore_accumulator(
                        city_accumulators.setdefault(city, PooledAccumulator()), snapshot
                    )
                continue
            try:
                _verify_sample_checksums(sample)
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
            except FileNotFoundError as exc:
                if not args.non_strict:
                    return _fail("REFERENCE_MISSING", str(exc))
                _record_failure(failures, sample.sample_id, "REFERENCE_MISSING", str(exc))
                continue
            except ValueError as exc:
                message = str(exc)
                code = message.split(":")[0] if ":" in message else "EVALUATION_FAILED"
                if not args.non_strict:
                    return _fail(code, message)
                _record_failure(failures, sample.sample_id, code, message)
                continue
            result = result.model_copy(
                update={
                    "checkpoint_sha256": checkpoint_sha256,
                    "upstream_revision": upstream_revision,
                    "repository_sha": repository_sha,
                }
            )
            results.append(result)
            snapshot = snapshot_accumulator(accumulator, calibrated - reference, reference)
            restore_accumulator(accumulator, snapshot)
            city = sample.source.get("city")
            if city:
                city_accumulator = city_accumulators.setdefault(city, PooledAccumulator())
                city_snapshot = snapshot_accumulator(
                    city_accumulator, calibrated - reference, reference
                )
                restore_accumulator(city_accumulator, city_snapshot)
            del calibrated, reference, loaded
            if resume_dir is not None:
                save_record(resume_dir, sample.sample_id, result, identity, snapshot)
        if not results:
            return _fail("EVALUATION_FAILED", "no samples completed")
        pooled = accumulator.summary()
        by_city_pooled = {
            city: city_accumulator.summary() for city, city_accumulator in city_accumulators.items()
        }
        total_seconds = round(time.perf_counter() - run_start, 3)
        run = evaluate_run(
            results,
            None,
            pooled=pooled,
            requested_samples=len(selected),
            failures=failures,
            by_city_pooled=by_city_pooled,
            timing_seconds={
                "model_load_seconds": model_load_seconds,
                "total_seconds": total_seconds,
                "per_sample_mean_seconds": round(total_seconds / max(len(selected), 1), 3),
            },
            dataset_release=document.get("release"),
            manifest_checksum=manifest_checksum,
            device=device,
        )
        run = run.model_copy(
            update={
                "checkpoint_sha256": checkpoint_sha256,
                "upstream_revision": upstream_revision,
                "repository_sha": repository_sha,
            }
        )
        per_sample = tuple(
            result.model_copy(
                update={
                    "checkpoint_sha256": checkpoint_sha256,
                    "upstream_revision": upstream_revision,
                    "repository_sha": repository_sha,
                }
            )
            for result in run.per_sample
        )
        run = run.model_copy(update={"per_sample": per_sample})
    finally:
        close = getattr(backend, "close", None)
        if callable(close):
            close()

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
