"""nDSM height backend: native-resolution tiling and the metric-height contract."""

from pathlib import Path
from typing import Any

import numpy as np

from depthwizard.backends.ndsm import HEIGHT_UNITS, HEIGHT_UNITS_KEY, NdsmBackend, tiled_predict
from depthwizard.contracts.semantics import DepthScale
from depthwizard.ingestion.api import inspect_input
from tests.ingestion.fixtures import make_png


class _ConstantModel:
    def __init__(self, config: dict[str, Any]) -> None:
        self.shapes: list[tuple[int, ...]] = []

    def __call__(self, patch: np.ndarray) -> np.ndarray:
        self.shapes.append(patch.shape)
        return np.full(patch.shape[:2], 7.5, dtype=np.float32)


def test_tiles_are_padded_to_patch_multiples_and_blend_exactly() -> None:
    rgb = np.zeros((500, 430, 3), dtype=np.uint8)
    model = _ConstantModel({})
    out = tiled_predict(model, rgb, tile=392, overlap=56)
    assert out.shape == (500, 430)
    assert np.allclose(out, 7.5)
    assert all(s[0] % 14 == 0 and s[1] % 14 == 0 for s in model.shapes)


def test_backend_declares_height_units_without_metric_claim(tmp_path: Path) -> None:
    backend = NdsmBackend(model_factory=_ConstantModel)
    result = backend.estimate_depth(inspect_input(make_png(tmp_path / "a.png")))
    assert result.depth_scale is DepthScale.RELATIVE
    assert result.units is None
    assert result.preprocessing[HEIGHT_UNITS_KEY] == HEIGHT_UNITS
    assert set(result.depth_values) == {7.5}
