"""Tests for solar angle resolution: metadata-first, explicit-override, and refusal."""

from __future__ import annotations

import pytest

from depthwizard.contracts.semantics import GeoreferencingLevel
from depthwizard.contracts.spatial import SpatialContext, SpatialKind
from depthwizard.errors import InvalidInputError
from depthwizard.ingestion.formats import DetectedFormat
from depthwizard.ingestion.models import InputHandle, InputInspection
from depthwizard.solar.sun_angles import SunAngles, resolve_sun_angles


def _make_inspection(meta: dict[str, str] | None = None) -> InputInspection:
    return InputInspection(
        handle=InputHandle(
            source_path="tile.tif",
            display_name="tile.tif",
            file_size=1024,
            sha256="a" * 64,
        ),
        detected_format=DetectedFormat.TIFF,
        width=100,
        height=100,
        georeferencing=GeoreferencingLevel.NON_GEOREFERENCED,
        spatial=SpatialContext(kind=SpatialKind.NOT_APPLICABLE),
        source_format_metadata=meta or {},
    )


def test_resolve_explicit_angles() -> None:
    """Explicit angles override metadata and report explicit source."""
    insp = _make_inspection({"SUN_ELEVATION": "30.0", "SUN_AZIMUTH": "120.0"})
    result = resolve_sun_angles(insp, sun_elevation_deg=45.0, sun_azimuth_deg=180.0)
    assert isinstance(result, SunAngles)
    assert result.elevation_deg == 45.0
    assert result.azimuth_deg == 180.0
    assert result.source == "explicit"


def test_resolve_metadata_angles() -> None:
    """Standard tag names in metadata are resolved when no explicit angles are given."""
    insp = _make_inspection({"SUN_ELEVATION": "38.5", "SUN_AZIMUTH": "145.2"})
    result = resolve_sun_angles(insp)
    assert result.elevation_deg == 38.5
    assert result.azimuth_deg == 145.2
    assert result.source == "metadata"


def test_resolve_metadata_solar_prefix() -> None:
    """Alternative SOLAR_ELEVATION and SOLAR_AZIMUTH tags are resolved."""
    insp = _make_inspection({"SOLAR_ELEVATION": "52.0", "SOLAR_AZIMUTH": "210.0"})
    result = resolve_sun_angles(insp)
    assert result.elevation_deg == 52.0
    assert result.azimuth_deg == 210.0
    assert result.source == "metadata"


def test_refuse_missing_both() -> None:
    """Refuse when neither metadata nor explicit angles are present."""
    insp = _make_inspection({})
    with pytest.raises(InvalidInputError, match="sun angles could not be resolved"):
        resolve_sun_angles(insp)


def test_refuse_partial_explicit() -> None:
    """Supplying only one angle explicitly raises InvalidInputError."""
    insp = _make_inspection({"SUN_ELEVATION": "30.0", "SUN_AZIMUTH": "120.0"})
    with pytest.raises(InvalidInputError, match="both elevation and azimuth"):
        resolve_sun_angles(insp, sun_elevation_deg=45.0)


def test_refuse_partial_metadata() -> None:
    """Metadata having only elevation but no azimuth is refused."""
    insp = _make_inspection({"SUN_ELEVATION": "30.0"})
    with pytest.raises(InvalidInputError, match="not sun azimuth"):
        resolve_sun_angles(insp)


def test_refuse_invalid_angles() -> None:
    """Elevation out of range (0, 90) or negative azimuth is refused at SunAngles validation."""
    insp = _make_inspection()
    with pytest.raises(ValueError, match="strictly inside"):
        resolve_sun_angles(insp, sun_elevation_deg=0.0, sun_azimuth_deg=100.0)
    with pytest.raises(ValueError, match="strictly inside"):
        resolve_sun_angles(insp, sun_elevation_deg=90.0, sun_azimuth_deg=100.0)
    with pytest.raises(ValueError, match=r"\[0, 360\)"):
        resolve_sun_angles(insp, sun_elevation_deg=45.0, sun_azimuth_deg=-5.0)
