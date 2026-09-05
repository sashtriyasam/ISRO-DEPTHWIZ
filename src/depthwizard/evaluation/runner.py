"""Evaluation orchestration: canonical pipeline, then held-out scoring.

Per sample: load → temp PNG → ``inspect_input`` → backend inference
(relative) → deterministic control/evaluation split → fit on controls
→ apply to evaluation pixels → score against the metric reference.
Run aggregation pools concatenated held-out pairs (primary); macro
means are reported alongside as the typical-sample view.
"""

from __future__ import annotations

import platform
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from depthwizard.calibration.apply import apply_calibration
from depthwizard.contracts.artifacts import DepthBackend
from depthwizard.contracts.semantics import DepthScale, ElevationSemantics
from depthwizard.errors import InvalidInputError
from depthwizard.evaluation.alignment import check_pixel_compatibility
from depthwizard.evaluation.datasets import LoadedSample
from depthwizard.evaluation.metrics import (
    compute_metrics,
    pool_metric_summaries,
    valid_evaluation_mask,
)
from depthwizard.evaluation.protocols import (
    CalibrationPlan,
    control_stride_split,
    fit_controls,
)
from depthwizard.evaluation.results import EvaluationResult, EvaluationRun
from depthwizard.version import __version__


def _repository_sha() -> str | None:
    """Current commit SHA when git metadata is available."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30
        )
    except Exception:
        return None
    sha = proc.stdout.strip()
    return sha if proc.returncode == 0 and sha else None


def _write_temp_png(rgb: np.ndarray, directory: Path) -> Path:
    """Materialize HWC uint8 RGB as a PNG for file-based inspection."""
    from PIL import Image

    array = np.ascontiguousarray(rgb)
    if array.ndim != 3 or array.shape[2] != 3 or array.dtype != np.uint8:
        raise InvalidInputError(f"evaluation input must be HWC uint8 RGB, got {array.shape}")
    path = directory / "eval-input.png"
    Image.fromarray(array, mode="RGB").save(path, format="PNG")
    return path


def run_sample(
    loaded: LoadedSample,
    backend: DepthBackend,
    target: ElevationSemantics = ElevationSemantics.HEIGHT_AGL_NDSM,
    stride: int = 8,
    dataset_release: str | None = None,
    manifest_checksum: str | None = None,
    device: str | None = None,
) -> tuple[EvaluationResult, np.ndarray, np.ndarray]:
    """Score one sample; also return held-out (calibrated, reference) pairs."""
    from depthwizard.ingestion import inspect_input

    sample = loaded.sample
    reference = loaded.reference
    if reference.units != "meters":
        raise ValueError(
            f"UNSUPPORTED_SEMANTICS: reference units must be 'meters', got {reference.units!r}"
        )
    if reference.semantics not in (
        ElevationSemantics.HEIGHT_AGL_NDSM,
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    ):
        raise ValueError(
            "UNSUPPORTED_SEMANTICS: reference must carry a metric meaning, "
            f"got {reference.semantics.value!r}"
        )
    if target != reference.semantics:
        raise ValueError(
            "UNSUPPORTED_SEMANTICS: calibration target "
            f"({target.value}) must equal the reference meaning "
            f"({reference.semantics.value}); no silent DSM/nDSM conversion"
        )

    with tempfile.TemporaryDirectory(prefix="dw-eval-") as tmp:
        inspection = inspect_input(str(_write_temp_png(loaded.image_rgb, Path(tmp))))
        depth = backend.estimate_depth(inspection)
    if depth.depth_scale is not DepthScale.RELATIVE:
        raise ValueError(
            f"evaluation requires a RELATIVE backend result, got {depth.depth_scale.value}"
        )
    height, width = reference.height, reference.width
    if (depth.output_resolution.width, depth.output_resolution.height) != (width, height):
        raise ValueError(
            "GRID_MISMATCH: backend output "
            f"{(depth.output_resolution.width, depth.output_resolution.height)} != "
            f"reference {(width, height)}"
        )
    spatial_details = depth.spatial.details
    alignment = check_pixel_compatibility(
        (height, width),
        (height, width),
        getattr(spatial_details, "crs", None) if spatial_details is not None else None,
        reference.crs,
    )

    predicted = np.asarray(depth.depth_values, dtype=np.float64).reshape(height, width)
    reference_values = np.asarray(reference.values, dtype=np.float64)
    base_valid = valid_evaluation_mask(
        predicted, reference_values, np.asarray(reference.valid_mask, dtype=bool)
    )
    control_mask, evaluation_mask = control_stride_split((height, width), base_valid, stride)
    calibration = fit_controls(
        predicted,
        reference_values,
        control_mask,
        reference_id=f"{sample.dataset_name}-eval-ref",
        target=target,
        source_checksum=depth.provenance.input_checksum,
    )
    eval_predicted = predicted[evaluation_mask]
    eval_reference = reference_values[evaluation_mask]
    if not np.isfinite(eval_predicted).all():
        raise ValueError("NO_VALID_PIXELS: evaluation pixels must be finite")
    calibrated = np.asarray(
        apply_calibration(tuple(float(value) for value in eval_predicted), calibration),
        dtype=np.float64,
    )
    # Score on the full grid so coverage reflects excluded controls/nodata.
    calibrated_full = np.full((height, width), float("nan"))
    calibrated_full[evaluation_mask] = calibrated
    metrics = compute_metrics(calibrated_full, reference_values, evaluation_mask, units="meters")
    plan = CalibrationPlan(
        protocol="control-stride",
        stride=stride,
        offset=0,
        reference_id=calibration.reference_id,
        target_semantics=target,
        control_pixels=int(control_mask.sum()),
        evaluation_pixels=int(evaluation_mask.sum()),
    )
    result = EvaluationResult(
        sample_id=sample.sample_id,
        dataset_name=sample.dataset_name,
        dataset_release=dataset_release,
        manifest_checksum=manifest_checksum,
        split=sample.split,
        model_name=depth.model_name,
        model_version=depth.model_version,
        checkpoint_id=depth.checkpoint_id,
        checkpoint_sha256=None,
        upstream_revision=None,
        input_checksum=depth.provenance.input_checksum,
        reference_id=calibration.reference_id,
        reference_checksum=sample.reference_checksum,
        reference_units=reference.units,
        reference_semantics=reference.semantics.value,
        calibration_method=calibration.method.value,
        calibration_scale=calibration.scale,
        calibration_offset=calibration.offset,
        calibration_rmse=calibration.rmse,
        calibration_r_squared=calibration.r_squared,
        calibration_controls=calibration.valid_samples,
        metrics=metrics,
        calibration_plan=plan,
        alignment=alignment,
        units="meters",
        product_semantics=target.value,
        device=device,
        python_version=platform.python_version(),
        engine_version=__version__,
        repository_sha=_repository_sha(),
    )
    return result, calibrated, eval_reference


def evaluate_sample(
    loaded: LoadedSample,
    backend: DepthBackend,
    target: ElevationSemantics = ElevationSemantics.HEIGHT_AGL_NDSM,
    stride: int = 8,
    dataset_release: str | None = None,
    manifest_checksum: str | None = None,
    device: str | None = None,
) -> EvaluationResult:
    """Score one sample end to end (summary only)."""
    result, _, _ = run_sample(
        loaded, backend, target, stride, dataset_release, manifest_checksum, device
    )
    return result


def evaluate_run(
    results: list[EvaluationResult],
    pairs: list[tuple[np.ndarray, np.ndarray]],
    calibration_protocol: str = "control-stride",
    alignment_protocol: str = "native-pixel",
    dataset_release: str | None = None,
    manifest_checksum: str | None = None,
    device: str | None = None,
) -> EvaluationRun:
    """Aggregate per-sample results; pool concatenated held-out pairs."""
    if not results:
        raise ValueError("EVALUATION_FAILED: no sample results to aggregate")
    if len(results) != len(pairs):
        raise ValueError("EVALUATION_FAILED: results and pairs disagree in count")
    first = results[0]
    total = sum(result.metrics.total_pixels for result in results)
    valid = sum(result.metrics.valid_pixels for result in results)
    pooled = compute_metrics(
        np.concatenate([np.asarray(pred, dtype=np.float64).ravel() for pred, _ in pairs]),
        np.concatenate([np.asarray(ref, dtype=np.float64).ravel() for _, ref in pairs]),
        None,
        units="meters",
    )
    macro = pool_metric_summaries([result.metrics for result in results])
    return EvaluationRun(
        dataset_name=first.dataset_name,
        dataset_release=dataset_release,
        manifest_checksum=manifest_checksum,
        split=first.split,
        sample_count=len(results),
        total_pixels=total,
        valid_pixels=valid,
        invalid_pixels=total - valid,
        coverage_fraction=(valid / total) if total else 0.0,
        pooled_mae=pooled.mae,
        pooled_rmse=pooled.rmse,
        pooled_r_squared=pooled.r_squared,
        macro=macro,
        per_sample=tuple(results),
        model_name=first.model_name,
        model_version=first.model_version,
        checkpoint_id=first.checkpoint_id,
        checkpoint_sha256=first.checkpoint_sha256,
        upstream_revision=first.upstream_revision,
        calibration_protocol=calibration_protocol,
        alignment_protocol=alignment_protocol,
        units="meters",
        product_semantics=first.product_semantics,
        device=device,
        python_version=platform.python_version(),
        engine_version=__version__,
        repository_sha=_repository_sha(),
    )
