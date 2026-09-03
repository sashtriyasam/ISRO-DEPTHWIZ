"""Deterministic tests for product provenance (unknown stays unknown)."""

from datetime import datetime

from depthwizard.contracts.provenance import ProductProvenance


def test_provenance_defaults_to_unknown() -> None:
    p = ProductProvenance()
    assert p.source_input_id is None
    assert p.input_checksum is None
    assert p.model_name is None
    assert p.model_version is None
    assert p.checkpoint_id is None
    assert p.calibration_method is None
    assert p.calibration_reference is None
    assert p.calibration_params is None
    assert p.software_version is None
    assert p.code_commit is None
    assert p.generated_at is None
    assert p.units is None
    assert p.semantic_meaning is None


def test_provenance_records_dem_reference() -> None:
    p = ProductProvenance(
        source_input_id="scene-042",
        calibration_method="dem_affine",
        calibration_reference="dem-ALOS-30m",
        calibration_params=(1.02, 0.35),
        units="meters",
        semantic_meaning="absolute_elevation_dsm",
        software_version="0.1.0",
        generated_at=datetime(2026, 9, 3, 12, 0, 0),
    )
    assert p.calibration_reference == "dem-ALOS-30m"
    assert p.calibration_params == (1.02, 0.35)
