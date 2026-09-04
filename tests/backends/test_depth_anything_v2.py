"""Depth Anything V2 backend: contract, semantics, preprocessing, provenance.

All tests use dependency injection (``model_factory``) so they run
without torch/cv2/depth_anything_v2 installed.  Real-model smoke tests
are gated behind actual dependency availability.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest

from depthwizard.backends.depth_anything_v2 import (
    CHECKPOINT_FILE,
    CHECKPOINT_HF_ID,
    CHECKPOINT_SHA,
    DEFAULT_INPUT_SIZE,
    ENCODER_CONFIG,
    MODEL_NAME,
    MODEL_VERSION,
    UPSTREAM_REVISION,
    UPSTREAM_URL,
    DepthAnythingV2Backend,
    _load_image_rgb,
)
from depthwizard.contracts.artifacts import ImageResolution
from depthwizard.contracts.semantics import (
    DepthScale,
    ElevationSemantics,
    GeoreferencingLevel,
)
from depthwizard.contracts.spatial import SpatialKind
from depthwizard.errors import InvalidInputError, ModelInferenceError
from depthwizard.ingestion import inspect_input
from depthwizard.version import __version__
from tests.ingestion.fixtures import make_jpeg, make_plain_tiff, make_png


def make_geotiff_rgb(path: Path) -> Path:
    """Write a 5×4 three-band uint8 GeoTIFF (EPSG:32643, nodata=0).

    DA-V2 requires 3-channel RGB input. The default ``make_geotiff``
    produces 2 bands, so DA-V2 tests use this helper instead.
    """
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeModel:
    """Deterministic fake model for injection: returns known H×W values."""

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
        """Return a deterministic depth map matching source H×W."""
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
    """Fake model that returns wrong output dimensions."""

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
    """Fake model that returns NaN values."""

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
) -> DepthAnythingV2Backend:
    """Create a DA-V2 backend with a fake checkpoint and injected model."""
    fake_ckpt = tmp_path / "fake.pth"
    fake_ckpt.write_bytes(b"fake-weights")
    return DepthAnythingV2Backend(
        checkpoint=fake_ckpt,
        device=device,
        model_factory=model_factory,
    )


# ---------------------------------------------------------------------------
# Backend contract
# ---------------------------------------------------------------------------


class TestBackendContract:
    """Verify DepthAnythingV2Backend implements DepthBackend protocol."""

    def test_protocol_conformance(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        protocol_attrs = {"model_name", "model_version", "checkpoint_id", "estimate_depth"}
        assert protocol_attrs <= set(dir(backend))

    def test_model_name(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        assert backend.model_name == "depth-anything-v2-small"

    def test_model_version(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        assert backend.model_version == MODEL_VERSION

    def test_checkpoint_id(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        assert backend.checkpoint_id == f"{CHECKPOINT_HF_ID}:{CHECKPOINT_FILE}"

    def test_callable_estimate_depth(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        assert callable(backend.estimate_depth)


# ---------------------------------------------------------------------------
# Relative semantics
# ---------------------------------------------------------------------------


class TestRelativeSemantics:
    """DA-V2 output must always be RELATIVE, never metric."""

    def test_png_relative(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        assert result.depth_scale is DepthScale.RELATIVE
        assert result.units is None
        assert result.units != "meters"
        assert result.elevation_semantics is ElevationSemantics.RELATIVE_DEPTH

    def test_geotiff_relative(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_geotiff_rgb(tmp_path / "scene.tif"))
        result = backend.estimate_depth(inspection)
        assert result.depth_scale is DepthScale.RELATIVE
        assert result.units is None
        assert result.elevation_semantics is ElevationSemantics.RELATIVE_DEPTH

    def test_no_calibration_provenance(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        assert result.provenance.calibration_method is None
        assert result.provenance.calibration_params is None
        assert result.provenance.calibration_reference is None


# ---------------------------------------------------------------------------
# Output dimensions
# ---------------------------------------------------------------------------


class TestOutputDimensions:
    """Verify input/output resolution match and value count."""

    def test_png_dimensions(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        # PNG_SIZE = (8, 6)
        assert result.input_resolution == ImageResolution(width=8, height=6)
        assert result.output_resolution == ImageResolution(width=8, height=6)
        assert len(result.depth_values) == 8 * 6

    def test_jpeg_dimensions(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_jpeg(tmp_path / "a.jpg"))
        result = backend.estimate_depth(inspection)
        # JPEG_SIZE = (10, 7)
        assert result.input_resolution == ImageResolution(width=10, height=7)
        assert result.output_resolution == ImageResolution(width=10, height=7)
        assert len(result.depth_values) == 10 * 7

    def test_geotiff_dimensions(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_geotiff_rgb(tmp_path / "scene.tif"))
        result = backend.estimate_depth(inspection)
        # TIFF_SIZE = (5, 4)
        assert result.input_resolution == ImageResolution(width=5, height=4)
        assert result.output_resolution == ImageResolution(width=5, height=4)
        assert len(result.depth_values) == 5 * 4

    def test_all_values_finite(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        assert all(math.isfinite(v) for v in result.depth_values)


# ---------------------------------------------------------------------------
# Output value preservation
# ---------------------------------------------------------------------------


class TestValuePreservation:
    """Backend wrapper must not normalize/scale/reinterpret model output."""

    def test_deterministic_fake_output(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        # Fake model produces sinusoidal pattern in [0, 1]
        assert all(0.0 <= v <= 1.0 for v in result.depth_values)
        # First value: 0.5 * (1 + sin(0) * cos(0)) = 0.5
        assert result.depth_values[0] == pytest.approx(0.5)

    def test_values_match_fake_model_directly(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        # Reconstruct expected from the same formula
        w, h = 8, 6
        expected = []
        for row in range(h):
            for col in range(w):
                expected.append(
                    0.5 * (1.0 + math.sin(2 * math.pi * col / w) * math.cos(2 * math.pi * row / h))
                )
        for i, (got, exp) in enumerate(zip(result.depth_values, expected, strict=True)):
            assert got == pytest.approx(exp), f"Mismatch at index {i}"


# ---------------------------------------------------------------------------
# Preprocessing record
# ---------------------------------------------------------------------------


class TestPreprocessingRecord:
    """Verify DepthResult.preprocessing records the actual configuration."""

    def test_preprocessing_keys(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        assert "entry" in result.preprocessing
        assert "input_color" in result.preprocessing
        assert "resize" in result.preprocessing
        assert "normalize" in result.preprocessing
        assert "tensor" in result.preprocessing
        assert "output_restore" in result.preprocessing


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


class TestProvenance:
    """Verify model metadata in canonical provenance structure."""

    def test_model_name_in_provenance(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        assert result.provenance.model_name == "depth-anything-v2-small"
        assert result.provenance.model_version == MODEL_VERSION

    def test_checkpoint_in_provenance(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        assert result.provenance.checkpoint_id == f"{CHECKPOINT_HF_ID}:{CHECKPOINT_FILE}"

    def test_input_checksum_linked(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        assert result.provenance.input_checksum == inspection.handle.sha256
        assert result.provenance.source_input_id == inspection.handle.display_name

    def test_software_version(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        assert result.provenance.software_version == __version__

    def test_units_none_for_relative(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        assert result.provenance.units is None

    def test_semantic_meaning(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        assert result.provenance.semantic_meaning is not None
        assert "relative" in result.provenance.semantic_meaning


# ---------------------------------------------------------------------------
# Georeference passthrough
# ---------------------------------------------------------------------------


class TestGeoreferencePassthrough:
    """CRS/transform/spatial metadata must pass through unchanged."""

    def test_png_non_georeferenced(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        assert result.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED
        assert result.spatial.kind is SpatialKind.NOT_APPLICABLE
        assert result.spatial.details is None

    def test_geotiff_preserves_crs(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_geotiff_rgb(tmp_path / "scene.tif"))
        result = backend.estimate_depth(inspection)
        assert result.georeferencing == inspection.georeferencing
        assert result.spatial == inspection.spatial
        assert result.spatial.details is not None
        assert result.spatial.details.crs == "EPSG:32643"

    def test_geotiff_still_relative(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        inspection = inspect_input(make_geotiff_rgb(tmp_path / "scene.tif"))
        result = backend.estimate_depth(inspection)
        # Georeferencing must not imply absolute elevation
        assert result.elevation_semantics is ElevationSemantics.RELATIVE_DEPTH
        assert result.units is None


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Clear failures for invalid inputs."""

    def test_rejects_non_inspection(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        with pytest.raises(InvalidInputError, match="InputInspection"):
            backend.estimate_depth("input-001")  # type: ignore[arg-type]

    def test_rejects_none_input(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        with pytest.raises(InvalidInputError, match="InputInspection"):
            backend.estimate_depth(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Checkpoint missing
# ---------------------------------------------------------------------------


class TestCheckpointMissing:
    """Missing checkpoint produces a clear ModelInferenceError."""

    def test_missing_checkpoint_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.pth"
        backend = DepthAnythingV2Backend(checkpoint=missing, device="cpu")
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        with pytest.raises(ModelInferenceError, match="checkpoint not found"):
            backend.estimate_depth(inspection)


# ---------------------------------------------------------------------------
# Torch missing
# ---------------------------------------------------------------------------


class TestTorchMissing:
    """Missing torch produces a clear ModelInferenceError."""

    def test_torch_missing_raises(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        import builtins

        real_import = builtins.__import__

        def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "torch":
                raise ImportError("No module named 'torch'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        backend = _make_backend(tmp_path)
        # Force _model to None so load() is called
        backend._model = None
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        with pytest.raises(ModelInferenceError, match="torch is required"):
            backend.estimate_depth(inspection)


# ---------------------------------------------------------------------------
# Device unavailable
# ---------------------------------------------------------------------------


class TestDeviceUnavailable:
    """Requesting unavailable device raises, no silent fallback."""

    def test_invalid_device_name(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Unknown device"):
            DepthAnythingV2Backend(checkpoint=tmp_path / "x.pth", device="tpu")


# ---------------------------------------------------------------------------
# Model output shape
# ---------------------------------------------------------------------------


class TestModelOutputShape:
    """Wrong model output dimensions produce ModelInferenceError."""

    def test_wrong_shape_raises(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path, model_factory=_WrongShapeModel)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        with pytest.raises(ModelInferenceError, match="must restore source size"):
            backend.estimate_depth(inspection)


# ---------------------------------------------------------------------------
# Non-finite output
# ---------------------------------------------------------------------------


class TestNonFiniteOutput:
    """NaN model output is allowed in the contract (valid_mask=None means
    all samples are assumed finite by downstream, but the contract does
    not reject NaN values in depth_values — it is the backend's
    responsibility to produce useful output)."""

    def test_nan_output_still_produces_result(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path, model_factory=_NanModel)
        inspection = inspect_input(make_png(tmp_path / "a.png"))
        result = backend.estimate_depth(inspection)
        # NaN values are technically valid depth_values (float tuple)
        assert len(result.depth_values) == 8 * 6
        assert result.depth_scale is DepthScale.RELATIVE


# ---------------------------------------------------------------------------
# Source immutability
# ---------------------------------------------------------------------------


class TestSourceImmutability:
    """Source inspection must not be mutated."""

    def test_inspection_unchanged(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        target = make_png(tmp_path / "a.png")
        before = target.read_bytes()
        inspection = inspect_input(target)
        backend.estimate_depth(inspection)
        assert target.read_bytes() == before

    def test_geotiff_inspection_unchanged(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        target = make_geotiff_rgb(tmp_path / "scene.tif")
        before = target.read_bytes()
        inspection = inspect_input(target)
        backend.estimate_depth(inspection)
        assert target.read_bytes() == before


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    """Two identical calls produce equivalent results."""

    def test_deterministic_output(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        target = make_png(tmp_path / "a.png")
        inspection = inspect_input(target)
        first = backend.estimate_depth(inspection)
        second = backend.estimate_depth(inspection)
        assert first.depth_values == second.depth_values
        assert first.model_name == second.model_name
        assert first.depth_scale == second.depth_scale


# ---------------------------------------------------------------------------
# Optional dependency
# ---------------------------------------------------------------------------


class TestOptionalDependency:
    """Importing the canonical package does not require torch."""

    def test_import_without_torch(self) -> None:
        """The module itself is importable without torch."""
        import importlib

        mod = importlib.import_module("depthwizard.backends.depth_anything_v2")
        assert hasattr(mod, "DepthAnythingV2Backend")


# ---------------------------------------------------------------------------
# Config dict
# ---------------------------------------------------------------------------


class TestConfigDict:
    """Backend capability reporting."""

    def test_config_dict_keys(self, tmp_path: Path) -> None:
        backend = _make_backend(tmp_path)
        cfg = backend.config_dict()
        assert cfg["backend"] == "depth-anything-v2-small"
        assert cfg["model"] == MODEL_NAME
        assert cfg["encoder"] == "vits"
        assert cfg["checkpoint_sha"] == CHECKPOINT_SHA
        assert cfg["upstream_revision"] == UPSTREAM_REVISION
        assert cfg["device"] == "cpu"


# ---------------------------------------------------------------------------
# Image loading
# ---------------------------------------------------------------------------


class TestImageLoading:
    """Verify _load_image_rgb handles all supported formats."""

    def test_load_png(self, tmp_path: Path) -> None:
        import numpy as np

        target = make_png(tmp_path / "a.png")
        inspection = inspect_input(target)
        arr = _load_image_rgb(inspection)
        assert arr.shape == (6, 8, 3)
        assert arr.dtype == np.uint8

    def test_load_jpeg(self, tmp_path: Path) -> None:
        import numpy as np

        target = make_jpeg(tmp_path / "a.jpg")
        inspection = inspect_input(target)
        arr = _load_image_rgb(inspection)
        assert arr.shape == (7, 10, 3)
        assert arr.dtype == np.uint8

    def test_load_geotiff(self, tmp_path: Path) -> None:
        import numpy as np

        target = make_geotiff_rgb(tmp_path / "scene.tif")
        inspection = inspect_input(target)
        arr = _load_image_rgb(inspection)
        assert arr.shape == (4, 5, 3)
        assert arr.dtype == np.uint8

    def test_load_plain_tiff_single_band(self, tmp_path: Path) -> None:
        import numpy as np

        target = make_plain_tiff(tmp_path / "a.tif")
        inspection = inspect_input(target)
        arr = _load_image_rgb(inspection)
        # Single-band TIFF should be expanded to 3-channel RGB
        assert arr.shape == (4, 5, 3)
        assert arr.dtype == np.uint8


# ---------------------------------------------------------------------------
# Metadata constants
# ---------------------------------------------------------------------------


class TestMetadataConstants:
    """Verify documented model metadata matches implementation."""

    def test_upstream_url(self) -> None:
        assert UPSTREAM_URL == "https://github.com/DepthAnything/Depth-Anything-V2"

    def test_upstream_revision(self) -> None:
        assert UPSTREAM_REVISION == "a561b849ebae10a6f5ef49e26c83cbbcd36c71bf"

    def test_checkpoint_sha(self) -> None:
        assert CHECKPOINT_SHA == "03876f8651c73a60fe4c2c48294e09fcb6838fcf"

    def test_encoder_config(self) -> None:
        assert ENCODER_CONFIG["encoder"] == "vits"
        assert ENCODER_CONFIG["features"] == 64
        assert ENCODER_CONFIG["out_channels"] == [48, 96, 192, 384]

    def test_default_input_size(self) -> None:
        assert DEFAULT_INPUT_SIZE == 518
