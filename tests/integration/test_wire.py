"""JSON round-trip, safety scan, payload size, pipeline bundle."""

import json
from pathlib import Path

import numpy as np

from depthwizard.backends.synthetic import SyntheticDepthBackend
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.integration import (
    bundle_from_pipeline,
    is_json_safe,
    terrain_product,
    terrain_product_from_json,
    to_json_text,
)
from depthwizard.pipeline import PipelineRequest, PipelineRunner
from tests.integration.support import (
    depth_fixture,
    dsm_fixture,
    full_pipeline_result,
    mesh_fixture,
)
from tests.pipeline.support import SyntheticCalibrationProvider


def test_terrain_json_round_trip(tmp_path: Path) -> None:
    product = terrain_product(
        depth_fixture(tmp_path), dsm_fixture(tmp_path), mesh_fixture(tmp_path)
    )
    text = to_json_text(product)
    parsed = json.loads(text)
    assert parsed["kind"] == "terrain"
    assert parsed["dsm"]["units"] == "meters"
    assert parsed["mesh"]["frame"] == "local"
    restored = terrain_product_from_json(text)
    assert restored == product


def test_json_safety_scan() -> None:
    assert is_json_safe(None)
    assert is_json_safe(True)
    assert is_json_safe(7)
    assert is_json_safe(2.5)
    assert is_json_safe("meters")
    assert is_json_safe([1, None, "x", {"k": [True]}])
    assert is_json_safe((1.0, 2.0))
    assert not is_json_safe(float("nan"))
    assert not is_json_safe(float("inf"))
    assert not is_json_safe(np.float64(1.0))
    assert not is_json_safe(np.bool_(True))
    assert not is_json_safe(np.int32(5))
    assert not is_json_safe(np.array([1.0]))
    assert not is_json_safe({1: "non-string-key"})
    import datetime

    assert not is_json_safe(datetime.datetime.now())


def test_payload_size_reasonable(tmp_path: Path) -> None:
    product = terrain_product(
        depth_fixture(tmp_path), dsm_fixture(tmp_path), mesh_fixture(tmp_path)
    )
    text = to_json_text(product)
    assert len(text) < 500_000
    parsed = json.loads(text)
    assert len(parsed["mesh"]["vertices"]) == 3 * 48
    assert len(parsed["dsm"]["values"]) == 48
    assert is_json_safe(parsed)


def test_bundle_from_pipeline(tmp_path: Path) -> None:
    result = full_pipeline_result(tmp_path, build_mesh=True)
    bundle = bundle_from_pipeline(result)
    assert bundle["status"] == "completed"
    assert bundle["states"][-1] == "completed"
    assert bundle["failure"] is None
    assert bundle["depth"] is not None
    assert bundle["calibration"] is not None
    assert bundle["dsm"] is not None
    assert bundle["mesh"] is not None
    assert bundle["geotiff_path"] == str(tmp_path / "out.tif")
    assert bundle["artifacts_available"] == [
        "depth",
        "calibration",
        "height",
        "dsm",
        "mesh",
        "geotiff",
    ]
    assert is_json_safe(bundle)
    text = json.dumps(bundle)
    assert "depth_values" in text  # present only inside explicit sections


def test_bundle_failed_run(tmp_path: Path) -> None:
    request = PipelineRequest(
        input_path=str(tmp_path / "missing.png"),
        backend=SyntheticDepthBackend(),
        calibration_provider=SyntheticCalibrationProvider(),
        target_semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
    )
    result = PipelineRunner().run(request)
    bundle = bundle_from_pipeline(result)
    assert bundle["status"] == "failed"
    assert bundle["failure"]["code"] == "InvalidInputError"
    assert bundle["failure"]["stage"] == "input_validated"
    assert bundle["depth"] is None
    assert bundle["artifacts_available"] == []
