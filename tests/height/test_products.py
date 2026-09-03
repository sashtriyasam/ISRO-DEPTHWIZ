"""AGL / absolute products, validation failures, model-level honesty."""

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from depthwizard.calibration import CalibrationResult, apply_calibration
from depthwizard.contracts.artifacts import DepthResult, ImageResolution
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import (
    DepthScale,
    ElevationSemantics,
    GeoreferencingLevel,
)
from depthwizard.contracts.spatial import SpatialContext, SpatialDetails, SpatialKind
from depthwizard.errors import CalibrationError
from depthwizard.height import ScientificHeightProduct, create_scientific_height_product
from tests.height.support import exact_calibration, png_chain


def test_agl_product(tmp_path: Path) -> None:
    depth, inspection = png_chain(tmp_path)
    calibration = exact_calibration(
        ElevationSemantics.HEIGHT_AGL_NDSM,
        source_checksum=inspection.handle.sha256,
    )
    product = create_scientific_height_product(
        depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM
    )
    assert isinstance(product, ScientificHeightProduct)
    assert product.units == "meters"
    assert product.semantics is ElevationSemantics.HEIGHT_AGL_NDSM
    assert (product.width, product.height) == (8, 6)
    assert product.values == apply_calibration(depth.depth_values, calibration)
    assert product.calibration_method == "scale_offset"
    assert product.calibration_reference == "ref-s10"
    assert (product.calibration_scale, product.calibration_offset) == (2.5, 10.0)
    assert product.calibration_valid_samples == 5
    assert product.source_checksum == inspection.handle.sha256
    assert product.source_input_id == inspection.handle.display_name


def test_absolute_product_has_no_datum(tmp_path: Path) -> None:
    depth, _ = png_chain(tmp_path)
    calibration = exact_calibration(ElevationSemantics.ABSOLUTE_ELEVATION_DSM)
    product = create_scientific_height_product(
        depth, calibration, ElevationSemantics.ABSOLUTE_ELEVATION_DSM
    )
    assert product.units == "meters"
    assert product.semantics is ElevationSemantics.ABSOLUTE_ELEVATION_DSM
    assert product.values == apply_calibration(depth.depth_values, calibration)
    assert not hasattr(product, "vertical_datum")


def test_relative_surface_source_accepted(tmp_path: Path) -> None:
    depth, _ = png_chain(tmp_path)
    surface = depth.model_copy(
        update={"elevation_semantics": ElevationSemantics.RELATIVE_SURFACE_RDSM}
    )
    calibration = exact_calibration(ElevationSemantics.HEIGHT_AGL_NDSM)
    product = create_scientific_height_product(
        surface, calibration, ElevationSemantics.HEIGHT_AGL_NDSM
    )
    assert product.semantics is ElevationSemantics.HEIGHT_AGL_NDSM


def test_determinism(tmp_path: Path) -> None:
    depth, _ = png_chain(tmp_path)
    calibration = exact_calibration(ElevationSemantics.HEIGHT_AGL_NDSM)
    first = create_scientific_height_product(depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM)
    second = create_scientific_height_product(
        depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM
    )
    assert first == second


def _metric_depth() -> DepthResult:
    return DepthResult(
        model_name="metric-model",
        input_resolution=ImageResolution(width=2, height=2),
        output_resolution=ImageResolution(width=2, height=2),
        depth_scale=DepthScale.METRIC,
        elevation_semantics=ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        georeferencing=GeoreferencingLevel.GEOREFERENCED_WITH_DEM,
        depth_values=(1.0, 2.0, 3.0, 4.0),
        units="meters",
        spatial=SpatialContext(kind=SpatialKind.PRESENT, details=SpatialDetails(crs="EPSG:4326")),
    )


def test_metric_depth_rejected(tmp_path: Path) -> None:
    calibration = exact_calibration(ElevationSemantics.ABSOLUTE_ELEVATION_DSM)
    with pytest.raises(CalibrationError, match="already claims"):
        create_scientific_height_product(
            _metric_depth(), calibration, ElevationSemantics.ABSOLUTE_ELEVATION_DSM
        )


def test_missing_calibration_rejected(tmp_path: Path) -> None:
    depth, _ = png_chain(tmp_path)
    with pytest.raises(TypeError, match="CalibrationResult"):
        create_scientific_height_product(depth, None, ElevationSemantics.HEIGHT_AGL_NDSM)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="DepthResult"):
        create_scientific_height_product(
            "depth",  # type: ignore[arg-type]
            exact_calibration(ElevationSemantics.HEIGHT_AGL_NDSM),
            ElevationSemantics.HEIGHT_AGL_NDSM,
        )


def _direct_result(**overrides: Any) -> CalibrationResult:
    base: dict[str, Any] = {
        "method": "scale_offset",
        "scale": 2.5,
        "offset": 10.0,
        "reference_id": "ref-direct",
        "reference_units": "meters",
        "target_semantics": ElevationSemantics.HEIGHT_AGL_NDSM,
        "total_samples": 5,
        "valid_samples": 5,
        "rmse": 0.0,
        "mae": 0.0,
        "max_abs_residual": 0.0,
        "r_squared": 1.0,
        "engine_version": "0.1.0",
    }
    base.update(overrides)
    return CalibrationResult(**base)


def test_nonfinite_calibration_rejected(tmp_path: Path) -> None:
    depth, _ = png_chain(tmp_path)
    bad = _direct_result(scale=float("inf"))
    with pytest.raises(CalibrationError, match="non-finite calibration"):
        create_scientific_height_product(depth, bad, ElevationSemantics.HEIGHT_AGL_NDSM)


def test_nonmeter_calibration_rejected(tmp_path: Path) -> None:
    depth, _ = png_chain(tmp_path)
    bad = _direct_result(reference_units="feet")
    with pytest.raises(CalibrationError, match="explicit-metre"):
        create_scientific_height_product(depth, bad, ElevationSemantics.HEIGHT_AGL_NDSM)


def test_semantic_mismatch_rejected(tmp_path: Path) -> None:
    depth, _ = png_chain(tmp_path)
    agl_calibration = exact_calibration(ElevationSemantics.HEIGHT_AGL_NDSM)
    with pytest.raises(CalibrationError, match="disagree"):
        create_scientific_height_product(
            depth, agl_calibration, ElevationSemantics.ABSOLUTE_ELEVATION_DSM
        )
    with pytest.raises(CalibrationError, match="metric meaning"):
        create_scientific_height_product(depth, agl_calibration, ElevationSemantics.RELATIVE_DEPTH)


def test_product_model_honesty() -> None:
    good: dict[str, Any] = {
        "values": (1.0, 2.0, 3.0, 4.0),
        "width": 2,
        "height": 2,
        "units": "meters",
        "semantics": ElevationSemantics.HEIGHT_AGL_NDSM,
        "georeferencing": GeoreferencingLevel.NON_GEOREFERENCED,
        "spatial": SpatialContext(kind=SpatialKind.NOT_APPLICABLE),
        "depth_model_name": "m",
        "calibration_method": "scale_offset",
        "calibration_reference": "r",
        "calibration_scale": 1.0,
        "calibration_offset": 0.0,
        "calibration_valid_samples": 3,
        "provenance": ProductProvenance(),
    }
    with pytest.raises(ValidationError, match="cardinality|value count|dimensions"):
        ScientificHeightProduct(**{**good, "values": (1.0,)})
    with pytest.raises(ValidationError, match="metric units"):
        ScientificHeightProduct(**{**good, "units": "feet"})
    with pytest.raises(ValidationError, match="metric meaning"):
        ScientificHeightProduct(**{**good, "semantics": ElevationSemantics.RELATIVE_DEPTH})
    with pytest.raises(ValidationError, match="finite"):
        ScientificHeightProduct(**{**good, "values": (1.0, 2.0, float("nan"), 4.0)})
