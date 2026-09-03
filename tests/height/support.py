"""Shared builders: full DepthResult→calibration chains from tiny fixtures."""

from pathlib import Path

from depthwizard.backends import SyntheticDepthBackend
from depthwizard.calibration import CalibrationResult, CalibrationSamples, ScaleOffsetCalibrator
from depthwizard.contracts.artifacts import DepthResult
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.ingestion import InputInspection, inspect_input
from tests.ingestion.fixtures import make_geotiff, make_png

EXACT_PREDICTED = (0.0, 1.0, 2.0, 3.0, 4.0)
EXACT_REFERENCE = (10.0, 12.5, 15.0, 17.5, 20.0)


def png_chain(tmp_path: Path) -> tuple[DepthResult, InputInspection]:
    """Synthetic relative depth + inspection for a non-georeferenced PNG."""
    inspection = inspect_input(make_png(tmp_path / "a.png"))
    return SyntheticDepthBackend().estimate_depth(inspection), inspection


def geotiff_chain(tmp_path: Path) -> tuple[DepthResult, InputInspection]:
    """Synthetic relative depth + inspection for a CRS-bearing GeoTIFF."""
    inspection = inspect_input(make_geotiff(tmp_path / "scene.tif"))
    return SyntheticDepthBackend().estimate_depth(inspection), inspection


def exact_calibration(
    target: ElevationSemantics,
    source_checksum: str | None = None,
    reference_id: str = "ref-s10",
) -> CalibrationResult:
    """Exact 2.5x+10 calibration for the requested metric target."""
    samples = CalibrationSamples(
        predicted_values=EXACT_PREDICTED,
        reference_values=EXACT_REFERENCE,
        reference_id=reference_id,
        reference_units="meters",
        target_semantics=target,
        source_checksum=source_checksum,
    )
    return ScaleOffsetCalibrator().calibrate(samples)
