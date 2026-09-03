"""Synthetic backend: construction, inference, determinism, semantics."""

import math
from pathlib import Path

import pytest

from depthwizard.backends import (
    MODEL_NAME,
    MODEL_VERSION,
    SyntheticDepthBackend,
    synthetic_depth_values,
)
from depthwizard.contracts.artifacts import DepthResult
from depthwizard.contracts.semantics import (
    DepthScale,
    ElevationSemantics,
    GeoreferencingLevel,
)
from depthwizard.contracts.spatial import SpatialKind
from depthwizard.ingestion import inspect_input
from depthwizard.version import __version__
from tests.ingestion.fixtures import (
    make_geotiff,
    make_jpeg,
    make_plain_tiff,
    make_png,
)


def test_construction_and_stable_metadata() -> None:
    backend = SyntheticDepthBackend()
    assert backend.model_name == MODEL_NAME == "synthetic-depth"
    assert backend.model_version == MODEL_VERSION == "0.1.0"
    assert backend.checkpoint_id is None
    # Structural conformance to the DepthBackend protocol boundary
    # (Protocol is not runtime_checkable, so conformance is asserted
    # by member presence, not isinstance).
    assert isinstance(backend.model_name, str)
    assert callable(backend.estimate_depth)


def test_protocol_conformance() -> None:
    protocol_attrs = {"model_name", "model_version", "checkpoint_id", "estimate_depth"}
    assert protocol_attrs <= set(dir(SyntheticDepthBackend()))


def test_png_produces_valid_result(tmp_path: Path) -> None:
    backend = SyntheticDepthBackend()
    inspection = inspect_input(make_png(tmp_path / "a.png"))
    result = backend.estimate_depth(inspection)
    assert isinstance(result, DepthResult)
    assert (result.output_resolution.width, result.output_resolution.height) == (8, 6)
    assert result.input_resolution == result.output_resolution
    assert len(result.depth_values) == 8 * 6
    assert all(math.isfinite(v) for v in result.depth_values)
    assert all(0.0 <= v <= 1.0 for v in result.depth_values)


def test_jpeg_and_tiff_inputs(tmp_path: Path) -> None:
    backend = SyntheticDepthBackend()
    jpeg = backend.estimate_depth(inspect_input(make_jpeg(tmp_path / "a.jpg")))
    assert (jpeg.output_resolution.width, jpeg.output_resolution.height) == (10, 7)
    assert len(jpeg.depth_values) == 10 * 7
    plain = backend.estimate_depth(inspect_input(make_plain_tiff(tmp_path / "a.tif")))
    assert (plain.output_resolution.width, plain.output_resolution.height) == (5, 4)
    assert len(plain.depth_values) == 5 * 4


def test_determinism_across_runs(tmp_path: Path) -> None:
    backend = SyntheticDepthBackend()
    target = make_png(tmp_path / "a.png")
    first = backend.estimate_depth(inspect_input(target))
    second = backend.estimate_depth(inspect_input(target))
    assert first == second
    assert first.depth_values == second.depth_values


def test_pattern_matches_closed_form() -> None:
    values = synthetic_depth_values(4, 3)
    assert len(values) == 12
    expected_first = 0.5 * (1.0 + math.sin(0.0) * math.cos(0.0))
    assert values[0] == pytest.approx(expected_first)
    assert values == synthetic_depth_values(4, 3)


def test_relative_semantics_never_metric(tmp_path: Path) -> None:
    backend = SyntheticDepthBackend()
    for target in (
        make_png(tmp_path / "a.png"),
        make_geotiff(tmp_path / "scene.tif"),
    ):
        result = backend.estimate_depth(inspect_input(target))
        assert result.depth_scale is DepthScale.RELATIVE
        assert result.units is None
        assert result.units != "meters"
        assert result.elevation_semantics is ElevationSemantics.RELATIVE_DEPTH


def test_georeferencing_preserved_not_invented(tmp_path: Path) -> None:
    backend = SyntheticDepthBackend()
    plain = backend.estimate_depth(inspect_input(make_png(tmp_path / "a.png")))
    assert plain.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED
    assert plain.spatial.kind is SpatialKind.NOT_APPLICABLE
    assert plain.spatial.details is None

    geo_inspection = inspect_input(make_geotiff(tmp_path / "scene.tif"))
    geo = backend.estimate_depth(geo_inspection)
    assert geo.georeferencing is GeoreferencingLevel.GEOREFERENCED_NO_ELEVATION_REFERENCE
    assert geo.spatial == geo_inspection.spatial
    assert geo.spatial.details is not None
    assert geo.spatial.details.crs == "EPSG:32643"
    # Still relative: georeferencing must not become absolute elevation.
    assert geo.elevation_semantics is ElevationSemantics.RELATIVE_DEPTH
    assert geo.units is None


def test_provenance_links_input(tmp_path: Path) -> None:
    backend = SyntheticDepthBackend()
    target = make_png(tmp_path / "a.png")
    inspection = inspect_input(target)
    result = backend.estimate_depth(inspection)
    provenance = result.provenance
    assert provenance.input_checksum == inspection.handle.sha256
    assert provenance.source_input_id == inspection.handle.display_name
    assert provenance.model_name == MODEL_NAME
    assert provenance.model_version == MODEL_VERSION
    assert provenance.checkpoint_id is None
    assert provenance.calibration_method is None
    assert provenance.calibration_params is None
    assert provenance.software_version == __version__
    assert provenance.generated_at is None  # omitted for bit-determinism
    assert provenance.units is None
    assert provenance.semantic_meaning is not None
    assert "synthetic" in provenance.semantic_meaning


def test_rejects_non_inspection_input() -> None:
    backend = SyntheticDepthBackend()
    with pytest.raises(TypeError, match="InputInspection"):
        backend.estimate_depth("input-001")  # type: ignore[arg-type]


def test_isolation_no_writes_no_mutation(tmp_path: Path) -> None:
    backend = SyntheticDepthBackend()
    target = make_geotiff(tmp_path / "scene.tif")
    before = target.read_bytes()
    snapshot = {child.name for child in tmp_path.iterdir()}
    backend.estimate_depth(inspect_input(target))
    assert target.read_bytes() == before
    assert {child.name for child in tmp_path.iterdir()} == snapshot
