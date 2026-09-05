"""Resumable evaluation: immutable per-sample records + identity gate.

After each sample, the runner writes ``<sample_id>.json`` containing the
run identity and the ``EvaluationResult``. A later invocation reloads
records whose identity matches exactly and skips re-inference for those
samples. Any identity change (manifest, model, checkpoint, protocols,
repository) forces re-evaluation — never silent reuse.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from depthwizard.evaluation.results import EvaluationResult

_ACCUMULATOR_KEYS = ("count", "sum_abs", "sum_sq_err", "sum_y", "sum_y2", "max_abs")


def run_identity(
    manifest_checksum: str | None,
    model_name: str,
    checkpoint_sha256: str | None,
    calibration_protocol: str,
    alignment_protocol: str,
    repository_sha: str | None,
    dataset_name: str,
    split: str,
    stride: int,
    target: str,
) -> dict[str, Any]:
    """Build the identity block a resume record must match (pure)."""
    return {
        "manifest_checksum": manifest_checksum,
        "model_name": model_name,
        "checkpoint_sha256": checkpoint_sha256,
        "calibration_protocol": calibration_protocol,
        "alignment_protocol": alignment_protocol,
        "repository_sha": repository_sha,
        "dataset_name": dataset_name,
        "split": split,
        "stride": stride,
        "target": target,
    }


def record_path(directory: Path, sample_id: str) -> Path:
    """Resume record location for one sample (pure)."""
    safe = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in sample_id)
    return directory / f"{safe}.json"


def save_record(
    directory: Path,
    sample_id: str,
    result: EvaluationResult,
    identity: dict[str, Any],
    accumulator: dict[str, float] | None = None,
) -> Path:
    """Persist one immutable sample record (overwrites its own id only).

    An optional accumulator snapshot (scalar error sums for this
    sample) lets resumed runs rebuild exact pooled metrics without
    retaining pixel arrays.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = record_path(directory, sample_id)
    document: dict[str, Any] = {"identity": identity, "result": result.model_dump(mode="json")}
    if accumulator is not None:
        document["accumulator"] = accumulator
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    return path


def load_record(
    directory: Path, sample_id: str, identity: dict[str, Any]
) -> tuple[EvaluationResult, dict[str, float]] | None:
    """Reload a record (plus accumulator) only on exact identity match."""
    path = record_path(directory, sample_id)
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    if not isinstance(document, dict) or document.get("identity") != identity:
        return None
    try:
        result = EvaluationResult(**document["result"])
        accumulator = document.get("accumulator")
    except (ValueError, TypeError):
        return None
    if not isinstance(accumulator, dict):
        return None
    try:
        snapshot = {key: float(accumulator[key]) for key in _ACCUMULATOR_KEYS}
    except (KeyError, TypeError, ValueError):
        return None
    return result, snapshot


def load_resume_records(
    directory: Path, sample_ids: list[str], identity: dict[str, Any]
) -> dict[str, tuple[EvaluationResult, dict[str, float]]]:
    """Collect all identity-matching records for the requested samples."""
    records: dict[str, tuple[EvaluationResult, dict[str, float]]] = {}
    for sample_id in sample_ids:
        record = load_record(directory, sample_id, identity)
        if record is not None:
            records[sample_id] = record
    return records


def restore_accumulator(accumulator: Any, snapshot: dict[str, float]) -> None:
    """Fold a stored per-sample snapshot into a live accumulator."""
    accumulator.count += int(snapshot["count"])
    accumulator.sum_abs += snapshot["sum_abs"]
    accumulator.sum_sq_err += snapshot["sum_sq_err"]
    accumulator.sum_y += snapshot["sum_y"]
    accumulator.sum_y2 += snapshot["sum_y2"]
    accumulator.max_abs = max(accumulator.max_abs, snapshot["max_abs"])


def snapshot_accumulator(accumulator: Any, errors: Any, references: Any) -> dict[str, float]:
    """Snapshot this sample's contribution (call before folding into the run)."""
    import numpy as np

    errors = np.asarray(errors, dtype=np.float64).ravel()
    references = np.asarray(references, dtype=np.float64).ravel()
    finite = np.isfinite(errors) & np.isfinite(references)
    errors = errors[finite]
    references = references[finite]
    absolute = np.abs(errors)
    return {
        "count": float(errors.size),
        "sum_abs": float(np.sum(absolute)),
        "sum_sq_err": float(np.sum(errors * errors)),
        "sum_y": float(np.sum(references)),
        "sum_y2": float(np.sum(references * references)),
        "max_abs": float(np.max(absolute)) if absolute.size else 0.0,
    }
