"""Service contract: serialization, validation, capabilities."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.service import (
    SERVICE_CONTRACT_VERSION,
    LocalService,
    ServiceCapabilities,
    ServiceRequest,
    decode_request,
    encode_request,
)
from tests.pipeline.support import png_input


def test_contract_version() -> None:
    assert SERVICE_CONTRACT_VERSION == "1"
    request = ServiceRequest(
        input_path="a.png", target_semantics=ElevationSemantics.HEIGHT_AGL_NDSM
    )
    assert request.contract_version == "1"


def test_request_round_trip() -> None:
    request = ServiceRequest(
        input_path="scene.png",
        target_semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
        build_mesh=True,
        geotiff_path="out.tif",
    )
    assert request.backend == "synthetic-depth"
    assert request.preprocessor == "identity"
    payload = json.loads(encode_request(request))
    assert payload["backend"] == "synthetic-depth"
    assert payload["target_semantics"] == "height_agl_ndsm"
    assert "callable" not in json.dumps(payload).lower()
    restored = decode_request(encode_request(request))
    assert restored == request


def test_request_rejects_blank_input() -> None:
    with pytest.raises(ValidationError):
        ServiceRequest(input_path="  ", target_semantics=ElevationSemantics.HEIGHT_AGL_NDSM)


def test_request_rejects_bad_semantics() -> None:
    with pytest.raises(ValidationError):
        ServiceRequest(input_path="a.png", target_semantics="relative_depth")  # type: ignore[arg-type]


def test_request_rejects_blank_geotiff() -> None:
    with pytest.raises(ValidationError):
        ServiceRequest(
            input_path="a.png",
            target_semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
            geotiff_path="  ",
        )


def test_capabilities(tmp_path: Path) -> None:
    _ = png_input(tmp_path)
    capabilities = LocalService().capabilities()
    assert isinstance(capabilities, ServiceCapabilities)
    assert capabilities.contract_version == "1"
    assert capabilities.supported_input_formats == [
        ".jpeg",
        ".jpg",
        ".png",
        ".tif",
        ".tiff",
    ]
    assert capabilities.supported_target_semantics == [
        "height_agl_ndsm",
        "absolute_elevation_dsm",
    ]
    assert capabilities.available_backends == ["synthetic-depth"]
    assert capabilities.mesh_supported is True
    assert capabilities.geotiff_supported is True
