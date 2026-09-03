"""Grid contract honesty: direct construction must satisfy every invariant."""

from typing import Any

import numpy as np
import pytest
from pydantic import ValidationError

from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import ElevationSemantics, GeoreferencingLevel
from depthwizard.contracts.spatial import SpatialContext, SpatialKind
from depthwizard.dsm import DSMGrid


def _good(**overrides: Any) -> DSMGrid:
    base: dict[str, Any] = {
        "array": np.ones((3, 4), dtype=np.float32),
        "valid_mask": np.ones((3, 4), dtype=bool),
        "width": 4,
        "height": 3,
        "dtype": "float32",
        "units": "meters",
        "semantics": ElevationSemantics.HEIGHT_AGL_NDSM,
        "nodata": float("nan"),
        "invalid_count": 0,
        "georeferencing": GeoreferencingLevel.NON_GEOREFERENCED,
        "spatial": SpatialContext(kind=SpatialKind.NOT_APPLICABLE),
        "depth_model_name": "m",
        "calibration_method": "scale_offset",
        "calibration_reference": "r",
        "calibration_scale": 1.0,
        "calibration_offset": 0.0,
        "calibration_valid_samples": 3,
        "provenance": ProductProvenance(),
    }
    base.update(overrides)
    return DSMGrid(**base)


def test_shape_mismatch_rejected() -> None:
    with pytest.raises(ValidationError, match="shape"):
        _good(array=np.ones((2, 2), dtype=np.float32))


def test_non_float_dtype_rejected() -> None:
    with pytest.raises(ValidationError, match="float32/float64"):
        _good(array=np.ones((3, 4), dtype=np.int32), dtype="int32")


def test_mask_shape_mismatch_rejected() -> None:
    with pytest.raises(ValidationError, match="valid_mask"):
        _good(valid_mask=np.ones((3, 3), dtype=bool))


def test_count_mismatch_rejected() -> None:
    with pytest.raises(ValidationError, match="invalid_count"):
        _good(invalid_count=2)


def test_mask_nodata_inconsistency_rejected() -> None:
    array = np.ones((3, 4), dtype=np.float32)
    mask = np.ones((3, 4), dtype=bool)
    mask[0, 0] = False  # masked but not NaN in the array
    with pytest.raises(ValidationError, match="NaN nodata marker"):
        _good(array=array, valid_mask=mask, invalid_count=1)


def test_nonfinite_valid_pixel_rejected() -> None:
    array = np.ones((3, 4), dtype=np.float32)
    array[1, 1] = float("inf")  # invalid value under a valid mask
    with pytest.raises(ValidationError, match="must all be finite"):
        _good(array=array)
