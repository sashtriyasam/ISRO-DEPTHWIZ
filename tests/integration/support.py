"""Deterministic transport fixtures (existing chains, no new science)."""

from pathlib import Path

from depthwizard.backends.synthetic import SyntheticDepthBackend
from depthwizard.calibration import (
    CalibrationResult,
    CalibrationSamples,
    ScaleOffsetCalibrator,
)
from depthwizard.contracts.artifacts import DepthResult
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.dsm import DSMGrid, rasterize_height_product
from depthwizard.height import create_scientific_height_product
from depthwizard.mesh import TerrainMesh, build_terrain_mesh
from depthwizard.pipeline import PipelineRequest, PipelineResult, PipelineRunner
from tests.height.support import exact_calibration, png_chain
from tests.ingestion.fixtures import make_png
from tests.pipeline.support import SyntheticCalibrationProvider


def depth_fixture(tmp_path: Path) -> DepthResult:
    """Synthetic relative depth from the PNG chain."""
    depth, _ = png_chain(tmp_path)
    return depth


def calibration_fixture() -> CalibrationResult:
    """Exact 2.5x+10 AGL calibration (independent of any depth)."""
    samples = CalibrationSamples(
        predicted_values=(0.0, 1.0, 2.0, 3.0, 4.0),
        reference_values=(10.0, 12.5, 15.0, 17.5, 20.0),
        reference_id="ref-transport",
        reference_units="meters",
        target_semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
    )
    return ScaleOffsetCalibrator().calibrate(samples)


def dsm_fixture(tmp_path: Path) -> DSMGrid:
    """AGL DSM grid from the PNG chain."""
    depth, inspection = png_chain(tmp_path)
    calibration = exact_calibration(
        ElevationSemantics.HEIGHT_AGL_NDSM,
        source_checksum=inspection.handle.sha256,
    )
    product = create_scientific_height_product(
        depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM
    )
    return rasterize_height_product(product)


def mesh_fixture(tmp_path: Path) -> TerrainMesh:
    """Terrain mesh built from the DSM fixture."""
    return build_terrain_mesh(dsm_fixture(tmp_path))


def full_pipeline_result(tmp_path: Path, build_mesh: bool = True) -> PipelineResult:
    """Completed pipeline result (mesh + export) for bundle tests."""
    make_png(tmp_path / "a.png")
    target = tmp_path / "out.tif"
    request = PipelineRequest(
        input_path=str(tmp_path / "a.png"),
        backend=SyntheticDepthBackend(),
        calibration_provider=SyntheticCalibrationProvider(),
        target_semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
        build_mesh=build_mesh,
        geotiff_path=str(target),
    )
    return PipelineRunner().run(request)
