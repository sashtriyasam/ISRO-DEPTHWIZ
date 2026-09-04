"""Semantics, provenance, boundary, immutability, determinism."""

import math
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.dem.build import build_terrain_reference
from depthwizard.dem.models import TerrainReferenceGrid
from depthwizard.version import __version__
from tests.dem.support import dem_inspection, image_target, native_grid


def test_terrain_semantics_not_dsm(tmp_path: Path) -> None:
    grid = native_grid(tmp_path)
    assert grid.semantics is ElevationSemantics.TERRAIN_ELEVATION
    assert grid.semantics.value not in (
        "absolute_elevation_dsm",
        "height_agl_ndsm",
    )
    assert grid.units == "meters"


def test_no_vertical_datum_field(tmp_path: Path) -> None:
    grid = native_grid(tmp_path)
    assert not hasattr(grid, "vertical_datum")
    assert not hasattr(grid, "datum")


def test_provenance_chain(tmp_path: Path) -> None:
    inspection = dem_inspection(tmp_path)
    grid = build_terrain_reference(inspection, image_target(tmp_path))
    provenance = grid.provenance
    assert provenance.source_input_id == "dem.tif"
    assert provenance.input_checksum == inspection.sha256
    assert provenance.units == "meters"
    assert provenance.semantic_meaning == "terrain_elevation"
    assert provenance.software_version == __version__
    assert provenance.generated_at is None
    assert provenance.checkpoint_id is None
    assert grid.source_dem_id == "dem.tif"
    assert grid.source_checksum == inspection.sha256
    assert grid.source_crs == "EPSG:32643"
    assert grid.source_resolution == 1.0
    assert grid.target_resolution == 0.5


def test_no_calibration_shortcut() -> None:
    import pathlib

    forbidden = (
        "CalibrationResult",
        "CalibrationSamples",
        "ScaleOffsetCalibrator",
        "apply_calibration",
        "create_scientific_height_product",
    )
    package = pathlib.Path(__file__).resolve().parent.parent.parent
    package = package / "src" / "depthwizard" / "dem"
    assert package.is_dir()
    for source in sorted(package.glob("*.py")):
        text = source.read_text(encoding="utf-8")
        for name in forbidden:
            assert name not in text, f"{source.name} references {name}"


def test_source_immutability(tmp_path: Path) -> None:
    from tests.dem.support import make_dem

    source = make_dem(tmp_path / "dem.tif")
    before = source.read_bytes()
    inspection = dem_inspection(tmp_path)
    target = image_target(tmp_path)
    first = build_terrain_reference(inspection, target)
    assert source.read_bytes() == before
    first.array[0, 0] = -1.0
    second = build_terrain_reference(inspection, target)
    assert second.array[0, 0] != -1.0
    assert source.read_bytes() == before


def test_determinism(tmp_path: Path) -> None:
    inspection = dem_inspection(tmp_path)
    target = image_target(tmp_path)
    first = build_terrain_reference(inspection, target)
    second = build_terrain_reference(inspection, target)
    assert bool(np.array_equal(first.array, second.array, equal_nan=True))
    assert bool((first.valid_mask == second.valid_mask).all())
    # NaN never equals itself: compare dumps with nodata excluded.
    assert first.model_dump(exclude={"array", "valid_mask", "nodata"}) == (
        second.model_dump(exclude={"array", "valid_mask", "nodata"})
    )
    assert math.isnan(first.nodata) and math.isnan(second.nodata)


def test_grid_model_rejects_nonterrain(tmp_path: Path) -> None:
    grid = native_grid(tmp_path)
    # model_copy skips validation, so revalidate explicitly.
    with pytest.raises(ValidationError, match="terrain-elevation meaning"):
        TerrainReferenceGrid.model_validate(
            {**grid.model_dump(), "semantics": ElevationSemantics.ABSOLUTE_ELEVATION_DSM}
        )
