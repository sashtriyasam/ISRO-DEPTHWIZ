"""Deterministic tests for DepthResult / DepthBackend contracts."""

from typing import Any

import pytest
from pydantic import ValidationError

from depthwizard.contracts.artifacts import (
    DepthBackend,
    DepthResult,
    ImageResolution,
)
from depthwizard.contracts.pipeline import PipelineState
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import (
    DepthScale,
    ElevationSemantics,
    GeoreferencingLevel,
)
from depthwizard.contracts.spatial import (
    AffineTransform,
    Bounds,
    SpatialContext,
    SpatialDetails,
    SpatialKind,
)


def _relative_result(**overrides: Any) -> DepthResult:
    base: dict[str, Any] = {
        "model_name": "test-backend",
        "input_resolution": ImageResolution(width=4, height=3),
        "output_resolution": ImageResolution(width=4, height=3),
        "depth_scale": DepthScale.RELATIVE,
        "elevation_semantics": ElevationSemantics.RELATIVE_DEPTH,
        "georeferencing": GeoreferencingLevel.NON_GEOREFERENCED,
        "depth_values": tuple(float(i) for i in range(12)),
        "spatial": SpatialContext(kind=SpatialKind.NOT_APPLICABLE),
    }
    base.update(overrides)
    return DepthResult(**base)


def test_enums_are_stable() -> None:
    assert {m.value for m in GeoreferencingLevel} == {
        "non_georeferenced",
        "georeferenced_no_elevation_reference",
        "georeferenced_with_dem",
        "georeferenced_with_gcp",
    }
    assert {m.value for m in DepthScale} == {"relative", "metric"}
    assert {m.value for m in ElevationSemantics} == {
        "relative_depth",
        "relative_surface_rdsm",
        "height_agl_ndsm",
        "absolute_elevation_dsm",
    }
    assert {m.value for m in SpatialKind} == {
        "present",
        "unavailable",
        "not_applicable",
    }
    assert {m.value for m in PipelineState} == {
        "input_validated",
        "preprocessing",
        "inference_running",
        "calibrating",
        "dsm_generation",
        "mesh_generation",
        "exporting",
        "completed",
        "failed",
        "cancelled",
    }


def test_valid_relative_result_without_fake_crs() -> None:
    result = _relative_result()
    assert result.units is None
    assert result.spatial.kind is SpatialKind.NOT_APPLICABLE
    assert result.spatial.details is None
    assert result.provenance.model_name is None  # unknown stays unknown


def test_relative_result_must_not_claim_meters() -> None:
    with pytest.raises(ValidationError):
        _relative_result(units="meters")


def test_metric_result_requires_meter_units() -> None:
    with pytest.raises(ValidationError):
        _relative_result(depth_scale=DepthScale.METRIC, units=None)
    metric = _relative_result(
        depth_scale=DepthScale.METRIC,
        elevation_semantics=ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        georeferencing=GeoreferencingLevel.GEOREFERENCED_WITH_DEM,
        units="meters",
        spatial=SpatialContext(
            kind=SpatialKind.PRESENT,
            details=SpatialDetails(crs="EPSG:4326"),
        ),
        provenance=ProductProvenance(
            calibration_method="dem_affine",
            calibration_reference="dem-ALOS-30m",
            units="meters",
        ),
    )
    assert metric.depth_scale is DepthScale.METRIC
    assert metric.units == "meters"


def test_relative_vs_metric_stay_distinguishable() -> None:
    relative = _relative_result()
    metric = _relative_result(
        depth_scale=DepthScale.METRIC,
        elevation_semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
        georeferencing=GeoreferencingLevel.GEOREFERENCED_WITH_GCP,
        units="meters",
        spatial=SpatialContext(
            kind=SpatialKind.PRESENT,
            details=SpatialDetails(crs="EPSG:32643"),
        ),
    )
    assert relative.depth_scale != metric.depth_scale
    assert relative.units != metric.units


def test_depth_length_must_match_output_resolution() -> None:
    with pytest.raises(ValidationError):
        _relative_result(depth_values=(1.0, 2.0))  # 2 != 12


def test_confidence_and_mask_lengths_validated() -> None:
    with pytest.raises(ValidationError):
        _relative_result(confidence_values=(0.5,))  # wrong length
    with pytest.raises(ValidationError):
        _relative_result(confidence_values=tuple([1.5] * 12))  # out of range
    with pytest.raises(ValidationError):
        _relative_result(valid_mask=(True, False))  # wrong length
    ok = _relative_result(
        confidence_values=tuple([0.9] * 12),
        valid_mask=tuple([True] * 11 + [False]),
    )
    assert ok.valid_mask is not None and ok.valid_mask[-1] is False


def test_non_georeferenced_cannot_carry_present_spatial() -> None:
    with pytest.raises(ValidationError):
        _relative_result(
            spatial=SpatialContext(
                kind=SpatialKind.PRESENT,
                details=SpatialDetails(crs="EPSG:4326"),
            )
        )


def test_georeferenced_metadata_carries_crs_transform_bounds() -> None:
    result = _relative_result(
        georeferencing=GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE,
        depth_scale=DepthScale.RELATIVE,
        elevation_semantics=ElevationSemantics.RELATIVE_SURFACE_RDSM,
        spatial=SpatialContext(
            kind=SpatialKind.PRESENT,
            details=SpatialDetails(
                crs="EPSG:32643",
                transform=AffineTransform(a=0.0, b=0.5, c=0.0, d=0.0, e=0.0, f=-0.5),
                bounds=Bounds(min_x=0.0, min_y=0.0, max_x=2.0, max_y=1.5),
                raster_width=4,
                raster_height=3,
                source="test-header",
            ),
        ),
    )
    assert result.spatial.details is not None
    assert result.spatial.details.crs == "EPSG:32643"
    assert result.spatial.details.transform is not None
    assert result.spatial.details.transform.as_tuple() == (0.0, 0.5, 0.0, 0.0, 0.0, -0.5)


def test_unavailable_spatial_carries_no_details() -> None:
    result = _relative_result(
        georeferencing=GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE,
        spatial=SpatialContext(kind=SpatialKind.UNAVAILABLE),
    )
    assert result.spatial.details is None


def test_backend_protocol_boundary() -> None:
    expected = _relative_result()

    class StubBackend:
        model_name = "stub"
        model_version: str | None = None
        checkpoint_id: str | None = None

        def estimate_depth(self, input_id: str) -> DepthResult:
            assert input_id == "input-001"
            return expected

    backend: DepthBackend = StubBackend()
    assert backend.estimate_depth("input-001") == expected
