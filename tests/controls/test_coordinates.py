"""Pixel/world controls, georeferencing gates, contradictions."""

from pathlib import Path

import pytest

from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.controls.build import build_reference_control
from depthwizard.controls.models import CoordinateSpace, SurfaceElevationControl
from depthwizard.dem.build import build_terrain_reference
from depthwizard.errors import GeospatialProcessingError, InvalidInputError, MissingCRSError
from tests.controls.support import relative_depth, surface, terrain_grid
from tests.dem.support import dem_inspection, image_target
from tests.height.support import geotiff_chain, png_chain


def test_pixel_control_prediction() -> None:
    depth = relative_depth((0.1, 0.4, 0.8), georeferenced=True)
    grid = terrain_grid((100.0, 105.0, 110.0))
    point = build_reference_control(
        depth,
        surface("p", 115.0, row=0, col=1),
        grid,
        ElevationSemantics.HEIGHT_AGL_NDSM,
    )
    assert (point.row, point.col) == (0, 1)
    assert point.predicted_value == 0.4
    assert (point.x, point.y) == (1.5, 0.5)
    assert point.reference_value == 10.0


def test_world_control_georeferenced(tmp_path: Path) -> None:
    depth, inspection = geotiff_chain(tmp_path)
    dem = dem_inspection(tmp_path)
    grid = build_terrain_reference(dem, image_target(tmp_path))
    # World point inside image pixel (0, 2): x in [101, 101.5).
    point = build_reference_control(
        depth,
        surface("w", 200.0, x=101.25, y=199.75),
        grid,
        ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    )
    assert (point.row, point.col) == (0, 2)
    assert point.pixel_col == pytest.approx(2.5)
    assert point.pixel_row == pytest.approx(0.5)
    assert point.reference_value == 200.0
    assert point.terrain_elevation_m is not None  # recorded context
    _ = inspection


def test_world_control_nongeoreferenced_fails(tmp_path: Path) -> None:
    depth, _ = png_chain(tmp_path)
    with pytest.raises(MissingCRSError, match="non-georeferenced"):
        build_reference_control(
            depth,
            surface("w", 200.0, x=1.0, y=1.0),
            None,
            ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        )


def test_coordinate_contradiction_rejected() -> None:
    depth = relative_depth((0.1, 0.4, 0.8), georeferenced=True)
    grid = terrain_grid((100.0, 105.0, 110.0))
    # Pixel (0, 1) center is (1.5, 0.5); claim far-away world instead.
    bad = SurfaceElevationControl(
        control_id="bad",
        coordinate_space=CoordinateSpace.PIXEL,
        row=0,
        col=1,
        x=999.0,
        y=999.0,
        surface_elevation_m=115.0,
        units="meters",
        source_id="survey-1",
    )
    with pytest.raises(GeospatialProcessingError, match="contradict"):
        build_reference_control(depth, bad, grid, ElevationSemantics.HEIGHT_AGL_NDSM)


def test_matching_dual_coordinates_accepted() -> None:
    depth = relative_depth((0.1, 0.4, 0.8), georeferenced=True)
    grid = terrain_grid((100.0, 105.0, 110.0))
    point = build_reference_control(
        depth,
        surface("ok", 115.0, row=0, col=1, x=1.5, y=0.5),
        grid,
        ElevationSemantics.HEIGHT_AGL_NDSM,
    )
    assert point.reference_value == 10.0


def test_crs_mismatch_rejected() -> None:
    depth = relative_depth((0.1, 0.4, 0.8), georeferenced=True)
    with pytest.raises(GeospatialProcessingError, match="differs"):
        build_reference_control(
            depth,
            surface("w", 200.0, x=1.0, y=1.0, crs="EPSG:4326"),
            None,
            ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        )


def test_out_of_bounds_pixel() -> None:
    depth = relative_depth((0.1, 0.4, 0.8), georeferenced=True)
    with pytest.raises(InvalidInputError, match="outside"):
        build_reference_control(
            depth,
            surface("oob", 200.0, row=0, col=9),
            None,
            ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        )


def test_world_outside_grid() -> None:
    depth = relative_depth((0.1, 0.4, 0.8), georeferenced=True)
    with pytest.raises(InvalidInputError, match="outside"):
        build_reference_control(
            depth,
            surface("oob", 200.0, x=-50.0, y=-50.0),
            None,
            ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        )
