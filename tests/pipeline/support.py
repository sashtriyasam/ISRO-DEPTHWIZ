"""Deterministic test collaborators (test-only, never production).

Reference acquisition is injected: these providers synthesize paired
references with a fixed rule (reference = 2.5 * predicted + 10) and fit
them with the real ScaleOffsetCalibrator. No DEM/GCP work exists here.
"""

from pathlib import Path
from typing import Any

from depthwizard.backends.synthetic import SyntheticDepthBackend
from depthwizard.calibration import (
    CalibrationResult,
    CalibrationSamples,
    ScaleOffsetCalibrator,
)
from depthwizard.contracts.artifacts import DepthResult
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.errors import CalibrationError, ModelInferenceError
from depthwizard.ingestion.models import InputInspection
from depthwizard.pipeline import (
    CancellationToken,
    PipelineRequest,
)
from tests.ingestion.fixtures import make_geotiff, make_png


class SyntheticCalibrationProvider:
    """Deterministic test provider reusing real OLS mathematics."""

    def __init__(
        self,
        target: ElevationSemantics = ElevationSemantics.HEIGHT_AGL_NDSM,
        reference_id: str = "synthetic-test-ref",
        checksum_override: str | None = None,
    ) -> None:
        """Configure target semantics and optional checksum override."""
        self._target = target
        self._reference_id = reference_id
        self._checksum_override = checksum_override

    @property
    def name(self) -> str:
        """Provider name."""
        return "synthetic-test-provider"

    def calibrate(self, depth_result: DepthResult) -> CalibrationResult:
        """Fit reference = 2.5 * predicted + 10 against depth values."""
        predicted = depth_result.depth_values
        reference = tuple(2.5 * value + 10.0 for value in predicted)
        checksum = (
            self._checksum_override
            if self._checksum_override is not None
            else depth_result.provenance.input_checksum
        )
        samples = CalibrationSamples(
            predicted_values=predicted,
            reference_values=reference,
            reference_id=self._reference_id,
            reference_units="meters",
            target_semantics=self._target,
            source_checksum=checksum,
        )
        return ScaleOffsetCalibrator().calibrate(samples)


class FailingBackend:
    """Backend that genuinely fails inference (no fake logic)."""

    model_name = "failing-backend"
    model_version: str | None = None
    checkpoint_id: str | None = None

    def estimate_depth(self, inspection: InputInspection) -> DepthResult:
        """Raise instead of inferring."""
        raise ModelInferenceError("synthetic inference boom")


class FailingProvider:
    """Provider that genuinely fails calibration."""

    @property
    def name(self) -> str:
        """Provider name."""
        return "failing-test-provider"

    def calibrate(self, depth_result: DepthResult) -> CalibrationResult:
        """Raise instead of calibrating."""
        raise CalibrationError("synthetic calibration boom")


class StripBackend:
    """Backend emitting a valid 4x1 relative result (mesh-hostile).

    Four pixels calibrate and rasterize fine, but a 4x1 grid has no
    2x2 quad, so mesh generation genuinely fails downstream.
    """

    model_name = "strip-backend"
    model_version: str | None = None
    checkpoint_id: str | None = None

    def estimate_depth(self, inspection: InputInspection) -> DepthResult:
        """Return a contract-valid single-row relative result."""
        from depthwizard.backends.synthetic import synthetic_depth_values
        from depthwizard.contracts.artifacts import ImageResolution
        from depthwizard.contracts.semantics import DepthScale, ElevationSemantics
        from depthwizard.contracts.spatial import SpatialContext, SpatialKind

        resolution = ImageResolution(width=4, height=1)
        return DepthResult(
            model_name=self.model_name,
            input_resolution=resolution,
            output_resolution=resolution,
            depth_scale=DepthScale.RELATIVE,
            elevation_semantics=ElevationSemantics.RELATIVE_DEPTH,
            georeferencing=inspection.georeferencing,
            depth_values=synthetic_depth_values(4, 1),
            spatial=SpatialContext(kind=SpatialKind.NOT_APPLICABLE)
            if inspection.spatial.kind is not SpatialKind.PRESENT
            else inspection.spatial,
        )


class CancellingProvider(SyntheticCalibrationProvider):
    """Provider requesting cancellation mid-run (boundary test)."""

    def __init__(self, token: CancellationToken) -> None:
        """Bind the token to cancel during calibration."""
        super().__init__()
        self._token = token

    def calibrate(self, depth_result: DepthResult) -> CalibrationResult:
        """Cancel, then delegate to the real deterministic fit."""
        self._token.cancel()
        return super().calibrate(depth_result)


def png_input(tmp_path: Path) -> str:
    """Create the deterministic PNG fixture, return its path string."""
    return str(make_png(tmp_path / "a.png"))


def geotiff_input(tmp_path: Path) -> str:
    """Create the deterministic GeoTIFF fixture, return its path string."""
    return str(make_geotiff(tmp_path / "scene.tif"))


def make_request(
    input_path: str,
    target: ElevationSemantics = ElevationSemantics.HEIGHT_AGL_NDSM,
    backend: Any = None,
    provider: Any = None,
    build_mesh: bool = False,
    geotiff_path: str | None = None,
    token: CancellationToken | None = None,
) -> PipelineRequest:
    """Build a deterministic pipeline request with test defaults."""
    return PipelineRequest(
        input_path=input_path,
        backend=backend if backend is not None else SyntheticDepthBackend(),
        calibration_provider=(
            provider if provider is not None else SyntheticCalibrationProvider(target)
        ),
        target_semantics=target,
        build_mesh=build_mesh,
        geotiff_path=geotiff_path,
        cancellation=token,
    )
