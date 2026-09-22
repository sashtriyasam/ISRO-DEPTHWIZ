"""Pipeline flat-depth variance detection tests."""

from __future__ import annotations

import math
from pathlib import Path

from depthwizard.contracts.artifacts import DepthResult, ImageResolution
from depthwizard.contracts.semantics import DepthScale, ElevationSemantics
from depthwizard.ingestion.models import InputInspection
from depthwizard.pipeline import PipelineRunner
from tests.ingestion.fixtures import make_png
from tests.pipeline.support import make_request


class FlatDepthBackend:
    """Backend that returns near-constant depth (flat)."""

    model_name = "flat-depth-test"
    model_version = "0.1.0"
    checkpoint_id = None

    def estimate_depth(self, inspection: InputInspection) -> DepthResult:
        h, w = inspection.height, inspection.width
        depth_values = tuple(0.5 for _ in range(h * w))  # perfectly flat
        return DepthResult(
            model_name=self.model_name,
            model_version=self.model_version,
            checkpoint_id=self.checkpoint_id,
            input_resolution=ImageResolution(width=w, height=h),
            output_resolution=ImageResolution(width=w, height=h),
            depth_scale=DepthScale.RELATIVE,
            elevation_semantics=ElevationSemantics.RELATIVE_DEPTH,
            georeferencing=inspection.georeferencing,
            depth_values=depth_values,
            spatial=inspection.spatial,
        )


class NormalDepthBackend:
    """Backend that returns varied depth (sinusoidal)."""

    model_name = "normal-depth-test"
    model_version = "0.1.0"
    checkpoint_id = None

    def estimate_depth(self, inspection: InputInspection) -> DepthResult:
        h, w = inspection.height, inspection.width
        vals = []
        for row in range(h):
            for col in range(w):
                vals.append(
                    0.5 * (1.0 + math.sin(2 * math.pi * col / w) * math.cos(2 * math.pi * row / h))
                )
        return DepthResult(
            model_name=self.model_name,
            model_version=self.model_version,
            checkpoint_id=self.checkpoint_id,
            input_resolution=ImageResolution(width=w, height=h),
            output_resolution=ImageResolution(width=w, height=h),
            depth_scale=DepthScale.RELATIVE,
            elevation_semantics=ElevationSemantics.RELATIVE_DEPTH,
            georeferencing=inspection.georeferencing,
            depth_values=tuple(vals),
            spatial=inspection.spatial,
        )


def test_flat_depth_warning(tmp_path: Path) -> None:
    """Flat depth output should produce a warning in pipeline result."""
    result = PipelineRunner().run(
        make_request(str(make_png(tmp_path / "a.png")), backend=FlatDepthBackend())
    )
    assert not result.succeeded
    assert result.failure is not None
    assert result.failure.stage.value == "calibrating"
    assert result.failure.error_category == "CalibrationError"
    assert "degenerate predictor" in result.failure.message
    assert any("Flat depth detected" in w for w in result.warnings)
    # Check the ratio is mentioned
    flat_warnings = [w for w in result.warnings if "Flat depth detected" in w]
    assert len(flat_warnings) == 1


def test_normal_depth_no_warning(tmp_path: Path) -> None:
    """Normal varied depth should not produce flat depth warning."""
    result = PipelineRunner().run(
        make_request(str(make_png(tmp_path / "a.png")), backend=NormalDepthBackend())
    )
    assert result.succeeded
    assert not any("Flat depth detected" in w for w in result.warnings)


def test_flat_depth_warning_before_calibration_fail(tmp_path: Path) -> None:
    """Flat depth warning is generated before calibration fails."""
    result = PipelineRunner().run(
        make_request(str(make_png(tmp_path / "a.png")), backend=FlatDepthBackend())
    )
    from depthwizard.contracts.pipeline import PipelineState

    assert result.state is PipelineState.FAILED
    assert result.failure is not None
    assert result.failure.stage is PipelineState.CALIBRATING
    # But the warning should still be present
    assert any("Flat depth detected" in w for w in result.warnings)
