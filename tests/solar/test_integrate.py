"""Tests for end-to-end solar shadow integration."""

from __future__ import annotations

import numpy as np

from depthwizard.contracts.semantics import GeoreferencingLevel
from depthwizard.contracts.spatial import (
    AffineTransform,
    SpatialContext,
    SpatialDetails,
    SpatialKind,
)
from depthwizard.ingestion.formats import DetectedFormat
from depthwizard.ingestion.models import InputHandle, InputInspection
from depthwizard.solar.integrate import SolarIntegrationResult, solar_observations_from_image
from depthwizard.solar.models import ShadowHeightConstraint


def _make_georeferenced_inspection(
    gsd: float = 0.5, meta: dict[str, str] | None = None
) -> InputInspection:
    transform = AffineTransform(a=gsd, b=0.0, c=1000.0, d=0.0, e=-gsd, f=2000.0)
    return InputInspection(
        handle=InputHandle(
            source_path="sat_scene.tif",
            display_name="sat_scene.tif",
            file_size=2048,
            sha256="b" * 64,
        ),
        detected_format=DetectedFormat.TIFF,
        width=100,
        height=100,
        georeferencing=GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE,
        spatial=SpatialContext(
            kind=SpatialKind.PRESENT,
            details=SpatialDetails(crs="EPSG:32643", transform=transform),
        ),
        source_format_metadata=meta or {},
    )


def test_solar_observations_end_to_end() -> None:
    """Detects shadows, uses metadata sun angles + GSD, returns valid constraints."""
    insp = _make_georeferenced_inspection(
        gsd=1.0, meta={"SUN_ELEVATION": "45.0", "SUN_AZIMUTH": "180.0"}
    )
    img = np.full((100, 100, 3), 220, dtype=np.uint8)
    img[20:50, 20:50, :] = 25  # 30x30 shadow

    res = solar_observations_from_image(insp, img)
    assert isinstance(res, SolarIntegrationResult)
    assert res.refused_reason is None
    assert res.detected_count >= 1
    assert res.count >= 1
    c = res.constraints[0]
    assert isinstance(c, ShadowHeightConstraint)
    assert c.units == "meters"
    assert c.height_m > 0.0
    assert "flat local ground" in c.assumptions[0]


def test_solar_refuses_when_no_angles_or_metadata() -> None:
    """Refuses gracefully with clear reason when sun angles are absent."""
    insp = _make_georeferenced_inspection(gsd=1.0, meta={})
    img = np.full((100, 100, 3), 200, dtype=np.uint8)
    img[20:40, 20:40, :] = 30

    res = solar_observations_from_image(insp, img)
    assert res.count == 0
    assert res.refused_reason is not None
    assert "sun angles could not be resolved" in res.refused_reason


def test_solar_refuses_when_no_gsd() -> None:
    """Refuses gracefully when GSD is missing and no override is given."""
    insp = InputInspection(
        handle=InputHandle(
            source_path="scene.png",
            display_name="scene.png",
            file_size=1024,
            sha256="c" * 64,
        ),
        detected_format=DetectedFormat.PNG,
        width=50,
        height=50,
        georeferencing=GeoreferencingLevel.NON_GEOREFERENCED,
        spatial=SpatialContext(kind=SpatialKind.NOT_APPLICABLE),
        source_format_metadata={"SUN_ELEVATION": "45.0", "SUN_AZIMUTH": "90.0"},
    )
    img = np.full((50, 50, 3), 200, dtype=np.uint8)
    img[10:30, 10:30, :] = 20

    res = solar_observations_from_image(insp, img)
    assert res.count == 0
    assert res.refused_reason is not None
    assert "GSD" in res.refused_reason


def test_solar_succeeds_with_gsd_override_on_png() -> None:
    """A non-georeferenced PNG succeeds if caller provides explicit gsd_override."""
    insp = InputInspection(
        handle=InputHandle(
            source_path="scene.png",
            display_name="scene.png",
            file_size=1024,
            sha256="d" * 64,
        ),
        detected_format=DetectedFormat.PNG,
        width=50,
        height=50,
        georeferencing=GeoreferencingLevel.NON_GEOREFERENCED,
        spatial=SpatialContext(kind=SpatialKind.NOT_APPLICABLE),
        source_format_metadata={},
    )
    img = np.full((50, 50, 3), 200, dtype=np.uint8)
    img[10:30, 10:30, :] = 20

    res = solar_observations_from_image(
        insp, img, sun_elevation_deg=45.0, sun_azimuth_deg=90.0, gsd_override=0.5
    )
    assert res.count >= 1
    assert res.refused_reason is None
    assert res.constraints[0].height_m > 0.0
