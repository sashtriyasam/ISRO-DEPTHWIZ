"""Immutability: sources never mutated, product frozen."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.height import create_scientific_height_product
from tests.height.support import exact_calibration, png_chain


def test_sources_unchanged(tmp_path: Path) -> None:
    depth, _ = png_chain(tmp_path)
    calibration = exact_calibration(ElevationSemantics.HEIGHT_AGL_NDSM)
    depth_before = depth.model_copy(deep=True)
    calibration_before = calibration.model_copy(deep=True)
    create_scientific_height_product(depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM)
    assert depth == depth_before
    assert calibration == calibration_before
    assert depth.depth_scale.value == "relative"
    assert depth.units is None


def test_product_immutable(tmp_path: Path) -> None:
    depth, _ = png_chain(tmp_path)
    calibration = exact_calibration(ElevationSemantics.HEIGHT_AGL_NDSM)
    product = create_scientific_height_product(
        depth, calibration, ElevationSemantics.HEIGHT_AGL_NDSM
    )
    with pytest.raises(ValidationError):
        product.units = "feet"
    with pytest.raises(ValidationError):
        product.values = (0.0,)
