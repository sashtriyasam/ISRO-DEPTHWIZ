"""Absolute and AGL reference construction (exact arithmetic)."""

from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.controls.build import (
    build_calibration_samples,
    build_reference_control,
)
from tests.controls.support import relative_depth, surface, terrain_grid


def test_absolute_control() -> None:
    depth = relative_depth((0.1, 0.4, 0.8))
    points = [
        build_reference_control(
            depth,
            surface(f"c{i}", elevation, row=0, col=i),
            None,
            ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        )
        for i, elevation in enumerate((110.0, 111.0, 112.0))
    ]
    assert [point.reference_value for point in points] == [110.0, 111.0, 112.0]
    assert [point.predicted_value for point in points] == [0.1, 0.4, 0.8]
    assert all(point.terrain_elevation_m is None for point in points)
    assert all(
        point.target_semantics is ElevationSemantics.ABSOLUTE_ELEVATION_DSM for point in points
    )
    samples = build_calibration_samples(points, reference_id="ref-abs")
    assert samples.predicted_values == (0.1, 0.4, 0.8)
    assert samples.reference_values == (110.0, 111.0, 112.0)
    assert samples.reference_units == "meters"
    assert samples.target_semantics is ElevationSemantics.ABSOLUTE_ELEVATION_DSM


def test_agl_control() -> None:
    depth = relative_depth((0.1, 0.4, 0.8), georeferenced=True)
    grid = terrain_grid((100.0, 105.0, 110.0))
    points = [
        build_reference_control(
            depth,
            surface(f"g{i}", elevation, row=0, col=i),
            grid,
            ElevationSemantics.HEIGHT_AGL_NDSM,
        )
        for i, elevation in enumerate((110.0, 115.0, 120.0))
    ]
    assert [point.reference_value for point in points] == [10.0, 10.0, 10.0]
    assert [point.terrain_elevation_m for point in points] == [100.0, 105.0, 110.0]
    samples = build_calibration_samples(points, reference_id="ref-agl")
    assert samples.reference_values == (10.0, 10.0, 10.0)
    assert samples.target_semantics is ElevationSemantics.HEIGHT_AGL_NDSM


def test_negative_agl_preserved() -> None:
    depth = relative_depth((0.5,), georeferenced=True)
    grid = terrain_grid((100.0,))
    point = build_reference_control(
        depth,
        surface("neg", 99.0, row=0, col=0),
        grid,
        ElevationSemantics.HEIGHT_AGL_NDSM,
    )
    assert point.reference_value == -1.0


def test_dem_is_not_surface() -> None:
    depth = relative_depth((0.5,), georeferenced=True)
    grid = terrain_grid((100.0,))
    absolute = build_reference_control(
        depth,
        surface("s", 120.0, row=0, col=0),
        grid,
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    )
    assert absolute.reference_value == 120.0
    assert absolute.reference_value != 100.0
    assert absolute.terrain_elevation_m == 100.0  # context only, not the reference
    agl = build_reference_control(
        depth,
        surface("s", 120.0, row=0, col=0),
        grid,
        ElevationSemantics.HEIGHT_AGL_NDSM,
    )
    assert agl.reference_value == 20.0


def test_agl_consistency() -> None:
    depth = relative_depth((0.2, 0.7), georeferenced=True)
    grid = terrain_grid((50.0, 60.0))
    points = [
        build_reference_control(
            depth,
            surface(f"h{i}", elevation, row=0, col=i),
            grid,
            ElevationSemantics.HEIGHT_AGL_NDSM,
        )
        for i, elevation in enumerate((57.5, 63.25))
    ]
    assert [point.reference_value for point in points] == [7.5, 3.25]
