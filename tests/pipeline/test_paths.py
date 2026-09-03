"""Execution paths: full, DSM-only, mesh/export permutations, preprocessing."""

from pathlib import Path

import numpy as np
import pytest

from depthwizard.contracts.pipeline import PipelineState
from depthwizard.errors import PipelineExecutionError
from depthwizard.pipeline import PipelineRunner
from tests.pipeline.support import geotiff_input, make_request, png_input


def test_full_path(tmp_path: Path) -> None:
    target = tmp_path / "out.tif"
    request = make_request(png_input(tmp_path), build_mesh=True, geotiff_path=str(target))
    result = PipelineRunner().run(request)
    assert result.state is PipelineState.COMPLETED
    assert result.succeeded
    assert result.states == (
        PipelineState.INPUT_VALIDATED,
        PipelineState.PREPROCESSING,
        PipelineState.INFERENCE_RUNNING,
        PipelineState.CALIBRATING,
        PipelineState.DSM_GENERATION,
        PipelineState.MESH_GENERATION,
        PipelineState.EXPORTING,
        PipelineState.COMPLETED,
    )
    assert result.inspection is not None
    assert result.depth is not None
    assert result.calibration is not None
    assert result.product is not None
    assert result.dsm is not None
    assert result.mesh is not None
    assert result.export is not None
    assert result.export.verified is True
    assert result.failure is None
    assert target.exists()


def test_dsm_only(tmp_path: Path) -> None:
    result = PipelineRunner().run(make_request(png_input(tmp_path)))
    assert result.state is PipelineState.COMPLETED
    assert result.states == (
        PipelineState.INPUT_VALIDATED,
        PipelineState.PREPROCESSING,
        PipelineState.INFERENCE_RUNNING,
        PipelineState.CALIBRATING,
        PipelineState.DSM_GENERATION,
        PipelineState.COMPLETED,
    )
    assert result.dsm is not None
    assert result.mesh is None
    assert result.export is None


def test_mesh_without_export(tmp_path: Path) -> None:
    result = PipelineRunner().run(make_request(png_input(tmp_path), build_mesh=True))
    assert result.state is PipelineState.COMPLETED
    assert result.states[-3:] == (
        PipelineState.DSM_GENERATION,
        PipelineState.MESH_GENERATION,
        PipelineState.COMPLETED,
    )
    assert PipelineState.EXPORTING not in result.states
    assert result.mesh is not None
    assert result.export is None


def test_export_without_mesh(tmp_path: Path) -> None:
    target = tmp_path / "out.tif"
    result = PipelineRunner().run(make_request(png_input(tmp_path), geotiff_path=str(target)))
    assert result.state is PipelineState.COMPLETED
    assert result.states[-3:] == (
        PipelineState.DSM_GENERATION,
        PipelineState.EXPORTING,
        PipelineState.COMPLETED,
    )
    assert PipelineState.MESH_GENERATION not in result.states
    assert result.mesh is None
    assert result.export is not None


def test_identity_preprocessing(tmp_path: Path) -> None:
    from tests.ingestion.fixtures import make_png

    source = make_png(tmp_path / "a.png")
    before = source.read_bytes()
    result = PipelineRunner().run(make_request(str(source)))
    assert result.state is PipelineState.COMPLETED
    assert PipelineState.PREPROCESSING in result.states
    assert source.read_bytes() == before
    assert result.inspection is not None
    assert result.inspection.handle.file_size == len(before)


def test_geotiff_input_path(tmp_path: Path) -> None:
    result = PipelineRunner().run(make_request(geotiff_input(tmp_path)))
    assert result.state is PipelineState.COMPLETED
    assert result.dsm is not None
    assert result.dsm.spatial.details is not None
    assert result.dsm.spatial.details.crs == "EPSG:32643"


def test_single_use_runner(tmp_path: Path) -> None:
    runner = PipelineRunner()
    runner.run(make_request(png_input(tmp_path)))
    with pytest.raises(PipelineExecutionError, match="single-use"):
        runner.run(make_request(png_input(tmp_path)))


def test_double_run_determinism(tmp_path: Path) -> None:
    first_path = png_input(tmp_path)
    first = PipelineRunner().run(make_request(first_path))
    second = PipelineRunner().run(make_request(first_path))
    assert first.states == second.states
    assert first.depth is not None and second.depth is not None
    assert first.depth.depth_values == second.depth.depth_values
    assert first.calibration is not None and second.calibration is not None
    assert first.calibration.scale == second.calibration.scale
    assert first.product is not None and second.product is not None
    assert first.product.values == second.product.values
    assert first.dsm is not None and second.dsm is not None
    assert bool(np.array_equal(first.dsm.array, second.dsm.array, equal_nan=True))
