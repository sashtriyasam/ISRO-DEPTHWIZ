"""Provenance: chain preserved, contradictions rejected, gaps tolerated."""

from pathlib import Path

import pytest

from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.errors import CalibrationError
from depthwizard.height import create_scientific_height_product
from depthwizard.version import __version__
from tests.height.support import exact_calibration, png_chain


def test_provenance_chain(tmp_path: Path) -> None:
    depth, inspection = png_chain(tmp_path)
    calibration = exact_calibration(
        ElevationSemantics.HEIGHT_AGL_NDSM,
        source_checksum=inspection.handle.sha256,
    )
    product = create_scientific_height_product(
        depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM
    )
    provenance = product.provenance
    assert isinstance(provenance, ProductProvenance)
    assert provenance.model_name == "synthetic-depth"
    assert provenance.model_version == "0.1.0"
    assert provenance.calibration_method == "scale_offset"
    assert provenance.calibration_reference == "ref-s10"
    assert provenance.calibration_params == (2.5, 10.0)
    assert provenance.units == "meters"
    assert provenance.semantic_meaning == "height_agl_ndsm"
    assert provenance.software_version == __version__
    assert provenance.source_input_id == inspection.handle.display_name
    assert provenance.input_checksum == inspection.handle.sha256
    assert provenance.generated_at is None
    assert product.depth_model_name == "synthetic-depth"
    assert product.source_checksum == inspection.handle.sha256


def test_contradictory_linkage_rejected(tmp_path: Path) -> None:
    depth, _ = png_chain(tmp_path)
    calibration = exact_calibration(
        ElevationSemantics.HEIGHT_AGL_NDSM,
        source_checksum="unrelated-source",
    )
    with pytest.raises(CalibrationError, match="contradiction"):
        create_scientific_height_product(depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM)


def test_absent_linkage_tolerated(tmp_path: Path) -> None:
    depth, _ = png_chain(tmp_path)
    bare_depth = depth.model_copy(
        update={"provenance": ProductProvenance()},
    )
    calibration = exact_calibration(ElevationSemantics.HEIGHT_AGL_NDSM)
    product = create_scientific_height_product(
        bare_depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM
    )
    assert product.source_input_id is None
    assert product.source_checksum is None
    assert product.provenance.calibration_reference == "ref-s10"
