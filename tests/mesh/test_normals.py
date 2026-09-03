"""Normals: upward orientation, slope direction, finiteness, fallback."""

import math

import numpy as np
import pytest

from depthwizard.mesh import build_terrain_mesh
from tests.mesh.support import flat_dsm, slope_dsm


def test_flat_normals_point_up() -> None:
    mesh = build_terrain_mesh(flat_dsm(3, 3, 5.0))
    assert bool(np.isfinite(mesh.normals).all())
    for normal in mesh.normals.tolist():
        assert normal == pytest.approx([0.0, 1.0, 0.0], abs=1e-12)


def test_slope_normals_constant_and_oriented() -> None:
    mesh = build_terrain_mesh(slope_dsm(4, 4))
    assert bool(np.isfinite(mesh.normals).all())
    expected = [-2.0 / math.sqrt(6.0), 1.0 / math.sqrt(6.0), -1.0 / math.sqrt(6.0)]
    for normal in mesh.normals.tolist():
        assert normal == pytest.approx(expected, rel=1e-12)
    assert bool((mesh.normals[:, 1] > 0.0).all())


def test_normals_deterministic() -> None:
    first = build_terrain_mesh(slope_dsm(4, 4))
    second = build_terrain_mesh(slope_dsm(4, 4))
    assert bool(np.array_equal(first.normals, second.normals))


def test_georeferenced_flat_normals_up() -> None:
    # North-up flipped frame exercises the winding-flip path.
    mesh = build_terrain_mesh(flat_dsm(3, 3, 7.0, georef=True))
    for normal in mesh.normals.tolist():
        assert normal == pytest.approx([0.0, 1.0, 0.0], abs=1e-12)


def test_normals_unit_length() -> None:
    mesh = build_terrain_mesh(slope_dsm(5, 4))
    lengths = np.sqrt((mesh.normals**2).sum(axis=1))
    assert bool(np.allclose(lengths, 1.0, rtol=1e-12, atol=1e-12))
