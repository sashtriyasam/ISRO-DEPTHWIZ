"""End-to-end service execution across output permutations."""

import json
from pathlib import Path

from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.service import (
    ArtifactKind,
    LocalService,
    ServiceRequest,
    decode_response,
    encode_response,
)
from tests.pipeline.support import SyntheticCalibrationProvider, png_input


def _request(
    input_path: str, build_mesh: bool = False, geotiff_path: str | None = None
) -> ServiceRequest:
    return ServiceRequest(
        input_path=input_path,
        target_semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
        build_mesh=build_mesh,
        geotiff_path=geotiff_path,
    )


def test_full_success(tmp_path: Path) -> None:
    target = tmp_path / "out.tif"
    request = _request(png_input(tmp_path), build_mesh=True, geotiff_path=str(target))
    response = LocalService().execute(request, SyntheticCalibrationProvider())
    assert response.success is True
    assert response.final_state == "completed"
    assert response.states == [
        "input_validated",
        "preprocessing",
        "inference_running",
        "calibrating",
        "dsm_generation",
        "mesh_generation",
        "exporting",
        "completed",
    ]
    assert response.failure is None
    by_kind = {artifact.kind: artifact for artifact in response.artifacts}
    assert set(by_kind) == set(ArtifactKind)
    depth = by_kind[ArtifactKind.DEPTH]
    assert depth.available and not depth.persisted
    assert depth.semantics == "relative_depth"
    assert depth.units is None
    assert (depth.width, depth.height) == (8, 6)
    assert depth.georeferenced is False
    height = by_kind[ArtifactKind.HEIGHT]
    assert height.semantics == ElevationSemantics.HEIGHT_AGL_NDSM.value
    assert height.units == "meters"
    assert (height.width, height.height) == (8, 6)
    dsm = by_kind[ArtifactKind.DSM]
    assert dsm.available and dsm.semantics == "height_agl_ndsm"
    mesh = by_kind[ArtifactKind.MESH]
    assert mesh.available and not mesh.persisted and mesh.path is None
    geotiff = by_kind[ArtifactKind.GEOTIFF]
    assert geotiff.available and geotiff.persisted
    assert geotiff.path == str(target)
    assert target.exists()
    summary = response.summary
    assert summary.backend_name == "synthetic-depth"
    assert summary.calibration_method == "scale_offset"
    assert summary.target_semantics == "height_agl_ndsm"
    assert summary.mesh_requested is True
    assert summary.input_checksum is not None


def test_dsm_only_descriptors(tmp_path: Path) -> None:
    response = LocalService().execute(_request(png_input(tmp_path)), SyntheticCalibrationProvider())
    assert response.success is True
    by_kind = {artifact.kind: artifact for artifact in response.artifacts}
    assert by_kind[ArtifactKind.DSM].available is True
    assert by_kind[ArtifactKind.MESH].available is False
    assert by_kind[ArtifactKind.GEOTIFF].available is False
    assert by_kind[ArtifactKind.GEOTIFF].persisted is False
    assert by_kind[ArtifactKind.GEOTIFF].path is None


def test_mesh_without_export(tmp_path: Path) -> None:
    response = LocalService().execute(
        _request(png_input(tmp_path), build_mesh=True),
        SyntheticCalibrationProvider(),
    )
    assert response.success is True
    by_kind = {artifact.kind: artifact for artifact in response.artifacts}
    assert by_kind[ArtifactKind.MESH].available is True
    assert by_kind[ArtifactKind.GEOTIFF].available is False
    assert "mesh_generation" in response.states
    assert "exporting" not in response.states


def test_export_without_mesh(tmp_path: Path) -> None:
    target = tmp_path / "out.tif"
    response = LocalService().execute(
        _request(png_input(tmp_path), geotiff_path=str(target)),
        SyntheticCalibrationProvider(),
    )
    assert response.success is True
    by_kind = {artifact.kind: artifact for artifact in response.artifacts}
    assert by_kind[ArtifactKind.MESH].available is False
    assert by_kind[ArtifactKind.GEOTIFF].available is True
    assert "mesh_generation" not in response.states


def test_no_arrays_in_wire_response(tmp_path: Path) -> None:
    request = _request(png_input(tmp_path), build_mesh=True)
    response = LocalService().execute(request, SyntheticCalibrationProvider())
    payload = encode_response(response)
    assert "depth_values" not in payload
    assert "vertices" not in payload
    assert "valid_mask" not in payload
    assert len(payload) < 5000


def test_response_round_trip(tmp_path: Path) -> None:
    request = _request(png_input(tmp_path), build_mesh=True)
    response = LocalService().execute(request, SyntheticCalibrationProvider())
    restored = decode_response(encode_response(response))
    assert restored.success == response.success
    assert restored.final_state == response.final_state
    assert restored.states == response.states
    assert restored.artifacts == response.artifacts
    assert restored.summary == response.summary
    assert json.loads(encode_response(response))["contract_version"] == "1"
