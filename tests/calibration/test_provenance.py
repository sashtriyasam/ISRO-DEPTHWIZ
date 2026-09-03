"""Provenance linkage: identifiers preserved, nothing fabricated."""

from depthwizard.calibration import CalibrationSamples, ScaleOffsetCalibrator
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.version import __version__


def test_provenance_round_trip() -> None:
    samples = CalibrationSamples(
        predicted_values=(0.0, 1.0, 2.0, 3.0, 4.0),
        reference_values=(10.0, 12.5, 15.0, 17.5, 20.0),
        reference_id="dem-ALOS-30m",
        reference_checksum="deadbeef",
        reference_units="meters",
        target_semantics=ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
        source_input_id="scene-042",
        source_checksum="cafef00d",
    )
    result = ScaleOffsetCalibrator().calibrate(samples)
    provenance = result.to_provenance()
    assert isinstance(provenance, ProductProvenance)
    assert provenance.calibration_method == "scale_offset"
    assert provenance.calibration_reference == "dem-ALOS-30m"
    assert provenance.calibration_params == (2.5, 10.0)
    assert provenance.units == "meters"
    assert provenance.semantic_meaning == "absolute_elevation_dsm"
    assert provenance.software_version == __version__
    assert provenance.source_input_id == "scene-042"
    assert provenance.input_checksum == "cafef00d"
    # Deterministic: no timestamps, no invented checkpoints/coordinates.
    assert provenance.generated_at is None
    assert provenance.checkpoint_id is None
    assert provenance.model_name is None


def test_provenance_unknowns_stay_unknown() -> None:
    samples = CalibrationSamples(
        predicted_values=(0.0, 1.0, 2.0),
        reference_values=(5.0, 6.0, 7.0),
        reference_id="ref-min",
        reference_units="meters",
        target_semantics=ElevationSemantics.HEIGHT_AGL_NDSM,
    )
    result = ScaleOffsetCalibrator().calibrate(samples)
    assert result.reference_checksum is None
    assert result.source_input_id is None
    assert result.source_checksum is None
    provenance = result.to_provenance()
    assert provenance.input_checksum is None
    assert provenance.source_input_id is None
    assert provenance.generated_at is None
