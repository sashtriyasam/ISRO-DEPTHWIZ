"""Deterministic quick-smoke: metric math validation, NOT a benchmark.

A 4x4 fixture with an exactly affine relative/reference pair exercises
the full sample path (split → fit → apply → score) with analytically
known outcomes (zero held-out error). Test-fixture data only.
"""

from __future__ import annotations

import numpy as np

from depthwizard.contracts.artifacts import DepthResult, ImageResolution
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import DepthScale, ElevationSemantics
from depthwizard.contracts.spatial import SpatialContext, SpatialKind
from depthwizard.evaluation.datasets import EvaluationSample, LoadedSample, ReferenceInfo
from depthwizard.evaluation.results import EvaluationResult
from depthwizard.evaluation.runner import evaluate_sample, run_sample
from depthwizard.ingestion.models import InputInspection
from depthwizard.version import __version__

SMOKE_WIDTH = 4
SMOKE_HEIGHT = 4


def smoke_reference() -> np.ndarray:
    """Known metric reference: arange(16) meters, all valid."""
    return np.arange(SMOKE_WIDTH * SMOKE_HEIGHT, dtype=np.float64).reshape(
        SMOKE_HEIGHT, SMOKE_WIDTH
    )


def smoke_relative() -> np.ndarray:
    """Exactly affine relative pair: (reference - 10) / 2.5."""
    return (smoke_reference() - 10.0) / 2.5


class SmokeBackend:
    """Test-only backend emitting the fixture relative pattern."""

    model_name = "smoke-backend"
    model_version: str | None = "0.0.0"
    checkpoint_id: str | None = None

    def estimate_depth(self, inspection: InputInspection) -> DepthResult:
        """Return the exact fixture pattern at the inspected resolution."""
        resolution = ImageResolution(width=inspection.width, height=inspection.height)
        values = tuple(float(value) for value in smoke_relative().ravel())
        if len(values) != inspection.width * inspection.height:
            raise ValueError("smoke fixture is 4x4 only")
        handle = inspection.handle
        return DepthResult(
            model_name=self.model_name,
            model_version=self.model_version,
            checkpoint_id=self.checkpoint_id,
            input_resolution=resolution,
            output_resolution=resolution,
            depth_scale=DepthScale.RELATIVE,
            elevation_semantics=ElevationSemantics.RELATIVE_DEPTH,
            georeferencing=inspection.georeferencing,
            depth_values=values,
            preprocessing={"smoke": "exact-affine-fixture"},
            units=None,
            spatial=SpatialContext(kind=SpatialKind.NOT_APPLICABLE),
            provenance=ProductProvenance(
                source_input_id=handle.display_name,
                input_checksum=handle.sha256,
                model_name=self.model_name,
                model_version=self.model_version,
                checkpoint_id=None,
                software_version=__version__,
                generated_at=None,
                units=None,
                semantic_meaning="smoke fixture (not scientific inference)",
            ),
        )


def smoke_loaded_sample() -> LoadedSample:
    """Build the in-memory 4x4 fixture (checker RGB + arange reference)."""
    rgb = np.zeros((SMOKE_HEIGHT, SMOKE_WIDTH, 3), dtype=np.uint8)
    for row in range(SMOKE_HEIGHT):
        for col in range(SMOKE_WIDTH):
            value = 255 if (row + col) % 2 == 0 else 0
            rgb[row, col] = (value, (col * 32) % 256, (row * 40) % 256)
    reference = smoke_reference()
    sample = EvaluationSample(
        sample_id="smoke-4x4",
        dataset_name="smoke",
        split="smoke",
        image_path="smoke.png",
        reference_path="smoke-ref.npy",
    )
    return LoadedSample(
        sample=sample,
        image_rgb=np.ascontiguousarray(rgb),
        reference=ReferenceInfo(
            values=np.ascontiguousarray(reference),
            width=SMOKE_WIDTH,
            height=SMOKE_HEIGHT,
            units="meters",
            semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
            crs=None,
            valid_mask=np.ones_like(reference, dtype=bool),
        ),
    )


def run_smoke() -> tuple[EvaluationResult, np.ndarray, np.ndarray]:
    """Execute the fixture path; expect ~zero held-out error."""
    return run_sample(smoke_loaded_sample(), SmokeBackend(), stride=4)


def smoke_result() -> EvaluationResult:
    """Summary-only smoke entry point."""
    return evaluate_sample(smoke_loaded_sample(), SmokeBackend(), stride=4)
