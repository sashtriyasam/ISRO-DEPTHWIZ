"""Validation, units, semantics, provenance, ordering, consumability."""

import math
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from depthwizard.calibration import MIN_VALID_SAMPLES, ScaleOffsetCalibrator
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.controls.build import (
    build_calibration_samples,
    build_reference_control,
)
from depthwizard.controls.models import ReferenceControlPoint
from depthwizard.errors import (
    CalibrationError,
    DemMismatchError,
    InvalidInputError,
    MissingElevationReferenceError,
)
from tests.controls.support import relative_depth, surface, terrain_grid


def _agl_points(**overrides: Any) -> list[ReferenceControlPoint]:
    depth = relative_depth((0.1, 0.4, 0.8), georeferenced=True)
    grid = terrain_grid((100.0, 105.0, 110.0))
    return [
        build_reference_control(
            depth,
            surface(f"g{i}", elevation, row=0, col=i),
            grid,
            ElevationSemantics.HEIGHT_AGL_NDSM,
        )
        for i, elevation in enumerate((110.0, 115.0, 120.0))
    ]


def test_invalid_surface_rejected() -> None:
    with pytest.raises(ValidationError):
        surface("nan", float("nan"), row=0, col=0)
    with pytest.raises(ValidationError):
        surface("inf", float("inf"), row=0, col=0)
    with pytest.raises(ValidationError):
        surface("neginf", float("-inf"), row=0, col=0)
    with pytest.raises(ValidationError, match="meters"):
        surface("feet", 100.0, row=0, col=0, units="feet")


def test_invalid_prediction_rejected() -> None:
    depth = relative_depth((0.1, float("nan"), 0.8), georeferenced=True)
    grid = terrain_grid((100.0, 105.0, 110.0))
    with pytest.raises(InvalidInputError, match="non-finite prediction"):
        build_reference_control(
            depth,
            surface("bad", 115.0, row=0, col=1),
            grid,
            ElevationSemantics.HEIGHT_AGL_NDSM,
        )
    masked = relative_depth((0.1, 0.4, 0.8), georeferenced=True, valid_mask=(True, False, True))
    with pytest.raises(InvalidInputError, match="invalid prediction cell"):
        build_reference_control(
            masked,
            surface("bad", 115.0, row=0, col=1),
            grid,
            ElevationSemantics.HEIGHT_AGL_NDSM,
        )


def test_nodata_terrain_rejected() -> None:
    depth = relative_depth((0.1, 0.4, 0.8), georeferenced=True)
    grid = terrain_grid((100.0, 105.0, 110.0), invalid=frozenset({0}))
    with pytest.raises(DemMismatchError, match="no valid terrain"):
        build_reference_control(
            depth,
            surface("hole", 115.0, row=0, col=0),
            grid,
            ElevationSemantics.HEIGHT_AGL_NDSM,
        )


def test_missing_terrain_for_agl() -> None:
    depth = relative_depth((0.1, 0.4, 0.8), georeferenced=True)
    with pytest.raises(MissingElevationReferenceError, match="DEM"):
        build_reference_control(
            depth,
            surface("g", 115.0, row=0, col=1),
            None,
            ElevationSemantics.HEIGHT_AGL_NDSM,
        )


def test_bad_target_rejected() -> None:
    depth = relative_depth((0.1, 0.4, 0.8))
    with pytest.raises(CalibrationError, match="metric height meanings"):
        build_reference_control(
            depth,
            surface("t", 115.0, row=0, col=1),
            None,
            ElevationSemantics.RELATIVE_DEPTH,
        )
    with pytest.raises(CalibrationError, match="metric height meanings"):
        build_reference_control(
            depth,
            surface("t", 115.0, row=0, col=1),
            None,
            ElevationSemantics.TERRAIN_ELEVATION,
        )


def test_metric_depth_rejected() -> None:
    depth = relative_depth((0.1, 0.4, 0.8))
    metric = depth.model_copy(update={"depth_scale": "metric", "units": "meters"})
    with pytest.raises(CalibrationError, match="RELATIVE"):
        build_reference_control(
            metric,
            surface("m", 115.0, row=0, col=1),
            None,
            ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        )


def test_empty_duplicates_mixed() -> None:
    with pytest.raises(InvalidInputError, match="at least one"):
        build_calibration_samples([], reference_id="r")
    with pytest.raises(InvalidInputError, match="reference identifier"):
        build_calibration_samples(_agl_points(), reference_id="")
    points = _agl_points()
    doubled = [points[0], points[0]]
    with pytest.raises(InvalidInputError, match="duplicate"):
        build_calibration_samples(doubled, reference_id="r")
    mixed = _agl_points()
    absolute = build_reference_control(
        relative_depth((0.1, 0.4, 0.8)),
        surface("a", 110.0, row=0, col=0),
        None,
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    )
    with pytest.raises(InvalidInputError, match="share their target"):
        build_calibration_samples([mixed[0], absolute], reference_id="r")


def test_order_and_cardinality() -> None:
    points = _agl_points()
    reordered = [points[2], points[0], points[1]]
    samples = build_calibration_samples(reordered, reference_id="order")
    assert samples.predicted_values == (0.8, 0.1, 0.4)
    assert samples.reference_values == (10.0, 10.0, 10.0)
    assert len(samples.predicted_values) == len(samples.reference_values) == 3
    assert samples.reference_id == "order"
    assert samples.reference_units == "meters"


def test_minimum_lives_in_s9() -> None:
    assert MIN_VALID_SAMPLES == 3
    depth = relative_depth((0.1, 0.4), georeferenced=True)
    grid = terrain_grid((100.0, 105.0))
    points = [
        build_reference_control(
            depth,
            surface(f"p{i}", elevation, row=0, col=i),
            grid,
            ElevationSemantics.HEIGHT_AGL_NDSM,
        )
        for i, elevation in enumerate((110.0, 115.0))
    ]
    samples = build_calibration_samples(points, reference_id="pair")
    assert len(samples.predicted_values) == 2
    with pytest.raises(CalibrationError, match="at least 3"):
        ScaleOffsetCalibrator().calibrate(samples)


def test_provenance_linkage() -> None:
    points = _agl_points()
    assert all(point.surface_source_id == "survey-1" for point in points)
    assert all(point.terrain_source_id == "dem-test" for point in points)
    assert all(point.depth_model == "test-backend" for point in points)
    samples = build_calibration_samples(points, reference_id="prov")
    assert samples.source_input_id is None
    assert samples.source_checksum is None


def test_provenance_with_depth_linkage(tmp_path: Path) -> None:
    from tests.height.support import png_chain

    depth, inspection = png_chain(tmp_path)
    grid = terrain_grid((100.0,) * 48)
    controls = [
        build_reference_control(
            depth,
            surface(f"c{i}", 200.0 + i, row=i // 8, col=i % 8),
            grid,
            ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        )
        for i in range(3)
    ]
    samples = build_calibration_samples(controls, reference_id="linked")
    assert samples.source_input_id == inspection.handle.display_name
    assert samples.source_checksum == inspection.handle.sha256


def test_immutability_and_determinism() -> None:
    depth = relative_depth((0.1, 0.4, 0.8), georeferenced=True)
    grid = terrain_grid((100.0, 105.0, 110.0))
    first = [
        build_reference_control(
            depth,
            surface(f"g{i}", elevation, row=0, col=i),
            grid,
            ElevationSemantics.HEIGHT_AGL_NDSM,
        )
        for i, elevation in enumerate((110.0, 115.0, 120.0))
    ]
    second = [
        build_reference_control(
            depth,
            surface(f"g{i}", elevation, row=0, col=i),
            grid,
            ElevationSemantics.HEIGHT_AGL_NDSM,
        )
        for i, elevation in enumerate((110.0, 115.0, 120.0))
    ]
    assert first == second
    assert depth.depth_values == (0.1, 0.4, 0.8)
    assert grid.array.tolist() == [[100.0, 105.0, 110.0]]
    assert build_calibration_samples(first, reference_id="d") == (
        build_calibration_samples(second, reference_id="d")
    )


def test_s9_consumability() -> None:
    samples = build_calibration_samples(_agl_points(), reference_id="fit")
    result = ScaleOffsetCalibrator().calibrate(samples)
    assert result.method.value == "scale_offset"
    assert math.isfinite(result.scale)
    assert result.reference_id == "fit"


def test_no_fitting_in_production() -> None:
    import pathlib

    forbidden = (
        "ScaleOffsetCalibrator",
        "apply_calibration",
        "create_scientific_height_product",
        "CalibrationResult",
    )
    package = pathlib.Path(__file__).resolve().parent.parent.parent
    package = package / "src" / "depthwizard" / "controls"
    assert package.is_dir()
    for source in sorted(package.glob("*.py")):
        text = source.read_text(encoding="utf-8")
        for name in forbidden:
            assert name not in text, f"{source.name} references {name}"
