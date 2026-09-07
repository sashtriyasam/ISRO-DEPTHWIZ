"""Solar-shadow geometry: trig identity, refusal paths, determinism."""

from __future__ import annotations

import math

import pytest

from depthwizard.errors import InvalidInputError
from depthwizard.solar import (
    PixelPoint,
    ShadowHeightConstraint,
    ShadowObservation,
    estimate_height,
    shadow_direction_deg,
)


def _observation(**overrides: object) -> ShadowObservation:
    """Build a valid observation (eastward shadow, 45° sun)."""
    params: dict[str, object] = {
        "source_input_id": "tile.png",
        "source_checksum": "abc123",
        "base": PixelPoint(row=10, col=10),
        "tip": PixelPoint(row=10, col=30),
        "shadow_length_px": 20.0,
        "gsd_m_per_px": 2.0,
        "sun_elevation_deg": 45.0,
        "sun_azimuth_deg": 270.0,
        "method": "manual-digitization-v1",
        "quality": "clear",
    }
    params.update(overrides)
    return ShadowObservation(**params)  # type: ignore[arg-type]


def test_trig_identity_at_45_degrees() -> None:
    """At 45° elevation, height equals length × GSD exactly."""
    constraint = estimate_height(_observation())
    assert constraint.height_m == pytest.approx(20.0 * 2.0 * 1.0)
    assert constraint.units == "meters"
    assert constraint.source_input_id == "tile.png"
    assert constraint.source_checksum == "abc123"
    assert "flat local ground" in constraint.assumptions[0]


def test_known_angle_value() -> None:
    """30° elevation gives length × GSD × tan(30°) (closed form)."""
    constraint = estimate_height(_observation(sun_elevation_deg=30.0))
    assert constraint.height_m == pytest.approx(40.0 * math.tan(math.radians(30.0)))


def test_direction_agreement_recorded() -> None:
    """Matching expected direction records agreement and stays valid."""
    constraint = estimate_height(_observation(expected_shadow_angle_deg=0.0))
    assert constraint.direction_agreement_deg == pytest.approx(0.0)


def test_direction_contradiction_refused() -> None:
    """Contradictory expected direction fails loudly (no guessed heights)."""
    observation = _observation(expected_shadow_angle_deg=90.0)
    with pytest.raises(InvalidInputError, match="disagrees with expected"):
        estimate_height(observation)


def test_unvalidated_direction_carries_assumption() -> None:
    """Without orientation knowledge the constraint says so explicitly."""
    constraint = estimate_height(_observation())
    assert constraint.direction_agreement_deg is None
    assert any("unvalidated" in assumption for assumption in constraint.assumptions)


def test_zero_elevation_refused_at_construction() -> None:
    """Horizon sun (0°) cannot produce a finite height."""
    with pytest.raises(ValueError, match="strictly inside"):
        _observation(sun_elevation_deg=0.0)


def test_overhead_sun_refused_at_construction() -> None:
    """Overhead sun (90°) casts no shadow."""
    with pytest.raises(ValueError, match="strictly inside"):
        _observation(sun_elevation_deg=90.0)


def test_zero_length_refused_at_construction() -> None:
    """Zero-length shadows are rejected."""
    with pytest.raises(ValueError):
        _observation(shadow_length_px=0.0)


def test_identical_endpoints_refused() -> None:
    """Base and tip must be distinct pixels."""
    with pytest.raises(ValueError, match="distinct pixels"):
        _observation(
            base=PixelPoint(row=5, col=5),
            tip=PixelPoint(row=5, col=5),
        )


def test_nonfinite_inputs_refused() -> None:
    """NaN/inf inputs never reach the trigonometric step."""
    with pytest.raises(ValueError):
        _observation(shadow_length_px=float("nan"))
    with pytest.raises(ValueError):
        _observation(gsd_m_per_px=float("inf"))


def test_rejects_non_observation() -> None:
    """Non-observation inputs fail with InvalidInputError."""
    with pytest.raises(InvalidInputError):
        estimate_height(None)  # type: ignore[arg-type]


def test_deterministic() -> None:
    """Repeat estimation is identical."""
    observation = _observation()
    assert estimate_height(observation) == estimate_height(observation)


def test_shadow_direction_convention() -> None:
    """Eastward shadow reads 0°, southward reads 90° (rows down)."""
    east = _observation()
    assert shadow_direction_deg(east) == pytest.approx(0.0)
    south = _observation(
        base=PixelPoint(row=10, col=10),
        tip=PixelPoint(row=30, col=10),
    )
    assert shadow_direction_deg(south) == pytest.approx(90.0)


def test_constraint_never_claims_ground_truth() -> None:
    """The constraint type carries assumptions and method, not certainty."""
    constraint = estimate_height(_observation())
    assert isinstance(constraint, ShadowHeightConstraint)
    assert len(constraint.assumptions) >= 4
    assert constraint.method == "manual-digitization-v1"
