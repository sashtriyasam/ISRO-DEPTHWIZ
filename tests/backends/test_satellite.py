"""Satellite-adapted DA-V2 backend: contract, semantics, tiling, provenance."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest

from depthwizard.backends.satellite import (
    BACKEND_ID,
    CHECKPOINT_FILE,
    CHECKPOINT_HF_ID,
    MODEL_NAME,
    MODEL_VERSION,
    TILE_OVERLAP,
    TILE_SIZE,
    SatelliteDepthBackend,
)
from depthwizard.contracts.artifacts import ImageResolution
from depthwizard.contracts.semantics import DepthScale, ElevationSemantics
from depthwizard.errors import InvalidInputError, ModelInferenceError
from depthwizard.ingestion import inspect_input
from tests.ingestion.fixtures import make_png


def make_geotiff_rgb(path: Path) -> Path:
    import numpy as np
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import Affine

    width, height = 5, 4
    grid = np.arange(width * height, dtype="uint8").reshape(height, width)
    transform = Affine(0.5, 0.0, 100.0, 0.0, -0.5, 200.0)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=3,
        dtype="uint8",
        crs=CRS.from_string("EPSG:32643"),
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(grid, 1)
        dst.write(grid, 2)
        dst.write(grid, 3)
    return path


class _FakeModel:
    def __init__(self, encoder_config: dict) -> None:
        self.encoder_config = encoder_config
        self._loaded = False

    def load_state_dict(self, state: Any) -> None:
        self._loaded = True

    def to(self, device: str) -> _FakeModel:
        return self

    def eval(self) -> _FakeModel:
        return self

    def infer_image(self, bgr: Any, input_size: int) -> Any:
        import numpy as np

        h, w = bgr.shape[:2]
        grid = np.zeros((h, w), dtype=np.float32)
        for row in range(h):
            for col in range(w):
                grid[row, col] = 0.5 * (
                    1.0 + math.sin(2 * math.pi * col / w) * math.cos(2 * math.pi * row / h)
                )
        return grid


class _WrongShapeModel:
    def __init__(self, encoder_config: dict) -> None:
        pass

    def load_state_dict(self, state: Any) -> None:
        pass

    def to(self, device: str) -> _WrongShapeModel:
        return self

    def eval(self) -> _WrongShapeModel:
        return self

    def infer_image(self, bgr: Any, input_size: int) -> Any:
        import numpy as np

        return np.zeros((64, 64), dtype=np.float32)


class _NanModel:
    def __init__(self, encoder_config: dict) -> None:
        pass

    def load_state_dict(self, state: Any) -> None:
        pass

    def to(self, device: str) -> _NanModel:
        return self

    def eval(self) -> _NanModel:
        return self

    def infer_image(self, bgr: Any, input_size: int) -> Any:
        import numpy as np

        h, w = bgr.shape[:2]
        return np.full((h, w), float("nan"), dtype=np.float32)


def _make_backend(
    tmp_path: Path,
    model_factory: Any = _FakeModel,
    device: str = "cpu",
    tile_size: int = TILE_SIZE,
    overlap: int = TILE_OVERLAP,
) -> SatelliteDepthBackend:
    fake_ckpt = tmp_path / "fake.pth"
    fake_ckpt.write_bytes(b"fake-weights")
    return SatelliteDepthBackend(
        checkpoint=fake_ckpt,
        device=device,
        tile_size=tile_size,
        overlap=overlap,
        model_factory=model_factory,
    )


class TestBackendContract:
    def test_protocol_conformance(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        assert {
            "model_name",
            "model_version",
            "checkpoint_id",
            "estimate_depth",
        } <= set(dir(backend))

    def test_model_name(self, tmp_path: Path) -> None:
        assert _make_backend(tmp_path).model_name == BACKEND_ID

    def test_model_version(self, tmp_path: Path) -> None:
        assert _make_backend(tmp_path).model_version == MODEL_VERSION

    def test_checkpoint_id(self, tmp_path: Path) -> None:
        assert _make_backend(tmp_path).checkpoint_id == f"{CHECKPOINT_HF_ID}:{CHECKPOINT_FILE}"

    def test_callable_estimate_depth(self, tmp_path: Path) -> None:
        assert callable(_make_backend(tmp_path).estimate_depth)


class TestRelativeSemantics:
    def test_png_relative(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        result = backend.estimate_depth(inspect_input(make_png(tmp_path / "a.png")))
        assert result.depth_scale is DepthScale.RELATIVE
        assert result.units is None
        assert result.elevation_semantics is ElevationSemantics.RELATIVE_DEPTH

    def test_geotiff_relative(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        result = backend.estimate_depth(inspect_input(make_geotiff_rgb(tmp_path / "scene.tif")))
        assert result.depth_scale is DepthScale.RELATIVE
        assert result.units is None
        assert result.elevation_semantics is ElevationSemantics.RELATIVE_DEPTH


class TestOutputDimensions:
    def test_png_dimensions(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        result = backend.estimate_depth(inspect_input(make_png(tmp_path / "a.png")))
        assert result.input_resolution == ImageResolution(width=8, height=6)
        assert result.output_resolution == ImageResolution(width=8, height=6)
        assert len(result.depth_values) == 8 * 6

    def test_all_values_finite(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        result = backend.estimate_depth(inspect_input(make_png(tmp_path / "a.png")))
        assert all(math.isfinite(v) for v in result.depth_values)


class TestTilingInference:
    def test_tiling_on_large_image(self, tmp_path: Path) -> None:
        # Use small tile_size to trigger tiling on the 8x6 PNG fixture
        backend = _make_backend(tmp_path, tile_size=4, overlap=1)
        result = backend.estimate_depth(inspect_input(make_png(tmp_path / "a.png")))
        assert result.output_resolution == ImageResolution(width=8, height=6)
        assert len(result.depth_values) == 48
        assert all(math.isfinite(v) for v in result.depth_values)

    def test_single_tile_no_tiling(self, tmp_path: Path) -> None:
        # Tile larger than image = direct inference path
        backend = _make_backend(tmp_path, tile_size=100, overlap=10)
        result = backend.estimate_depth(inspect_input(make_png(tmp_path / "a.png")))
        assert result.output_resolution == ImageResolution(width=8, height=6)
        assert len(result.depth_values) == 48


class TestInputValidation:
    def test_rejects_non_inspection(self, tmp_path: Path) -> None:
        with pytest.raises(InvalidInputError, match="InputInspection"):
            _make_backend(tmp_path).estimate_depth("input-001")  # type: ignore


class TestCheckpointMissing:
    def test_missing_checkpoint_raises(self, tmp_path: Path) -> None:
        backend = SatelliteDepthBackend(checkpoint=tmp_path / "missing.pth", device="cpu")
        with pytest.raises(ModelInferenceError, match="checkpoint not found"):
            backend.estimate_depth(inspect_input(make_png(tmp_path / "a.png")))


class TestDeterminism:
    def test_deterministic_output(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        target = make_png(tmp_path / "a.png")
        inspection = inspect_input(target)
        first = backend.estimate_depth(inspection)
        second = backend.estimate_depth(inspection)
        assert first.depth_values == second.depth_values
        assert first.model_name == second.model_name


class TestProvenance:
    def test_model_name_in_provenance(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        result = backend.estimate_depth(inspect_input(make_png(tmp_path / "a.png")))
        assert result.provenance.model_name == BACKEND_ID
        assert result.provenance.model_version == MODEL_VERSION

    def test_input_checksum_linked(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        assert result.provenance.input_checksum == inspection.handle.sha256


class TestConfigDict:
    def test_config_dict_keys(self, tmp_path: Path) -> None:
        cfg = _make_backend(tmp_path).config_dict()
        assert cfg["backend"] == BACKEND_ID
        assert cfg["model"] == MODEL_NAME
        assert cfg["encoder"] == "vits"
        assert cfg["tile_size"] == TILE_SIZE
        assert cfg["tile_overlap"] == TILE_OVERLAP
