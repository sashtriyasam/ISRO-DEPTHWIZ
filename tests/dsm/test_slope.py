"""Slope analysis: exact gradients, nodata propagation, honest refusal."""

from __future__ import annotations

import math

import numpy as np
import pytest

from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.contracts.spatial import SpatialContext, SpatialDetails, SpatialKind
from depthwizard.dsm.slope import SLOPE_UNIT, SlopeGrid, compute_slope
from depthwizard.errors import InvalidInputError
from tests.mesh.support import flat_dsm, holed_dsm


def _ramp_dsm() -> object:
    """5×4 georeferenced grid with elevation[row, col] = 2*col + row."""
    grid = flat_dsm(5, 4, 0.0, georef=True)
    array = grid.array.copy()
    for row in range(4):
        for col in range(5):
            array[row, col] = 2.0 * col + 1.0 * row
    return grid.model_copy(update={"array": array})


def test_flat_terrain_zero_slope() -> None:
    """Flat georeferenced terrain yields 0° on every valid interior pixel."""
    slope = compute_slope(flat_dsm(5, 4, 10.0, georef=True))
    assert isinstance(slope, SlopeGrid)
    assert slope.units == SLOPE_UNIT
    assert (slope.width, slope.height) == (5, 4)
    # Interior 3×2 pixels valid; one-pixel border invalid (no extrapolation).
    assert int(slope.valid_mask.sum()) == 3 * 2
    assert bool((slope.array[slope.valid_mask] == 0.0).all())


def test_ramp_matches_closed_form() -> None:
    """Planar ramp slope equals atan(hypot(dzdx, dzdy)) exactly."""
    slope = compute_slope(_ramp_dsm())  # type: ignore[arg-type]
    # dz/dcol = 2 m/px, dz/drow = 1 m/px, step = 0.5 m.
    expected = math.degrees(math.atan(math.hypot(2.0 / 0.5, 1.0 / 0.5)))
    interior = slope.array[1:-1, 1:-1][slope.valid_mask[1:-1, 1:-1]]
    assert interior.size == 6
    assert bool((np.abs(interior - expected) < 1e-9).all())


def test_holes_propagate_to_neighbours() -> None:
    """Any pixel touching nodata (3×3) is invalid — holes never bridged."""
    slope = compute_slope(holed_dsm(5, 4, 10.0, {(1, 1)}, georef=True))
    assert not slope.valid_mask[1, 1]
    assert not slope.valid_mask[1, 2]
    assert not slope.valid_mask[2, 1]
    assert not slope.valid_mask[2, 2]


def test_nongeoreferenced_grid_refused() -> None:
    """Grids without spatial context cannot yield metric slope."""
    with pytest.raises(InvalidInputError, match="PRESENT spatial context"):
        compute_slope(flat_dsm(5, 4, 10.0, georef=False))


def test_degree_grid_refused_not_converted() -> None:
    """Geographic-degree grids are refused, never silently converted."""
    grid = flat_dsm(5, 4, 10.0, georef=True)
    assert grid.spatial.details is not None
    details = grid.spatial.details.model_copy(update={"crs": "EPSG:4326", "units": "degrees"})
    spatial = SpatialContext(kind=SpatialKind.PRESENT, details=details)
    degree_grid = grid.model_copy(update={"spatial": spatial})
    with pytest.raises(InvalidInputError, match="metric planimetric units"):
        compute_slope(degree_grid)


def test_unknown_crs_refused() -> None:
    """Unparseable CRS identifiers fail loudly."""
    grid = flat_dsm(5, 4, 10.0, georef=True)
    assert grid.spatial.details is not None
    details = grid.spatial.details.model_copy(update={"crs": "not-a-crs"})
    spatial = SpatialContext(kind=SpatialKind.PRESENT, details=details)
    bad_grid = grid.model_copy(update={"spatial": spatial})
    with pytest.raises(InvalidInputError, match="cannot interpret CRS"):
        compute_slope(bad_grid)


def test_missing_gsd_refused() -> None:
    """Spatial context without resolution cannot yield slope."""
    grid = flat_dsm(5, 4, 10.0, georef=True)
    assert grid.spatial.details is not None
    details = grid.spatial.details.model_copy(update={"resolution_gsd": None})
    spatial = SpatialContext(kind=SpatialKind.PRESENT, details=details)
    bad_grid = grid.model_copy(update={"spatial": spatial})
    with pytest.raises(InvalidInputError, match="resolution_gsd"):
        compute_slope(bad_grid)


def test_source_grid_unchanged() -> None:
    """Slope derivation never mutates the source DSM grid."""
    grid = flat_dsm(5, 4, 10.0, georef=True)
    before = grid.array.copy()
    compute_slope(grid)
    assert bool((grid.array == before).all())


def test_deterministic_and_semantics_preserved() -> None:
    """Repeat runs are identical; source meaning flows through."""
    grid = flat_dsm(5, 4, 10.0, georef=True)
    first = compute_slope(grid)
    second = compute_slope(grid)
    assert bool(np.array_equal(first.array, second.array, equal_nan=True))
    assert bool((first.valid_mask == second.valid_mask).all())
    assert first.derived_from_semantics is ElevationSemantics.HEIGHT_AGL_NDSM
    assert first.georeferencing == grid.georeferencing
    assert first.calibration_method == grid.calibration_method


def test_rejects_non_grid() -> None:
    """Non-DSM inputs fail with InvalidInputError."""
    with pytest.raises(InvalidInputError):
        compute_slope(None)  # type: ignore[arg-type]


def test_explicit_metric_units_accepted() -> None:
    """Recorded metric planimetric units take the explicit path."""
    grid = flat_dsm(5, 4, 10.0, georef=True)
    assert grid.spatial.details is not None
    details = grid.spatial.details.model_copy(update={"units": "meters"})
    spatial = SpatialContext(kind=SpatialKind.PRESENT, details=details)
    metric_grid = grid.model_copy(update={"spatial": spatial})
    slope = compute_slope(metric_grid)
    assert int(slope.valid_mask.sum()) == 6


def test_spatial_details_importable() -> None:
    """Guard the SpatialDetails shape this module depends on."""
    assert SpatialDetails.model_fields.keys() >= {"crs", "resolution_gsd", "units"}
