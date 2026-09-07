"""M17 GeoNRW structural-adaptation backend: contract, semantics, provenance.

All tests use dependency injection (``model_factory``) so they run
without the M17 head implementation or the ``best.pt`` checkpoint.
torch is required (reproducibility seeding mirrors the canonical
adapter); real-head inference stays unavailable by design here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from depthwizard.backends.m17 import (
    BACKEND_ID,
    CHECKPOINT_FILE,
    CHECKPOINT_SHA256,
    DEFAULT_INPUT_SIZE,
    M10_ZMU,
    M10_ZSIGMA,
    MODEL_NAME,
    MODEL_VERSION,
    UPSTREAM_REVISION,
    UPSTREAM_URL,
    M17DepthBackend,
)
from depthwizard.contracts.semantics import (
    DepthScale,
    ElevationSemantics,
    GeoreferencingLevel,
)
from depthwizard.errors import InvalidInputError, ModelInferenceError
from depthwizard.ingestion import inspect_input
from depthwizard.version import __version__
from tests.ingestion.fixtures import make_jpeg, make_png


class _FakeM17Model:
    """Deterministic fake M17 head: returns known H×W values."""

    def infer_image(self, features: Any, input_size: int) -> Any:
        import math

        import numpy as np

        h, w = features.shape[:2]
        grid = np.zeros((h, w), dtype=np.float64)
        for row in range(h):
            for col in range(w):
                grid[row, col] = 0.5 * (
                    1.0 + math.sin(2 * math.pi * col / w) * math.cos(2 * math.pi * row / h)
                )
        return grid


def _make_backend(tmp_path: Path) -> M17DepthBackend:
    """Create an M17 backend with a fake checkpoint and injected model."""
    fake_ckpt = tmp_path / "fake-best.pt"
    fake_ckpt.write_bytes(b"fake-m17-weights")
    return M17DepthBackend(
        checkpoint=fake_ckpt,
        device="cpu",
        model_factory=_FakeM17Model,
    )


def test_backend_identity() -> None:
    """Backend advertises the canonical M17 identity (never DA-V2's)."""
    assert BACKEND_ID == "m17-geonrw-struct"
    backend = M17DepthBackend.__new__(M17DepthBackend)
    assert backend.model_name == "m17-geonrw-struct"
    assert backend.model_version == MODEL_VERSION
    assert backend.checkpoint_id == f"m17-geonrw-struct-e01:{CHECKPOINT_FILE}"


def test_constants_match_frozen_candidate() -> None:
    """Checkpoint hash, upstream pin and zstats match the frozen decision."""
    assert CHECKPOINT_SHA256 == "D7C0BE9127FAFAC5F4C2D207E3626D335AF148A8CBB7489A10EE8C7F7DA4EDAC"
    assert UPSTREAM_REVISION == "a561b849ebae10a6f5ef49e26c83cbbcd36c71bf"
    assert UPSTREAM_URL == "https://github.com/DepthAnything/Depth-Anything-V2"
    assert M10_ZMU == 8.037330237035235
    assert M10_ZSIGMA == 10.304011604437477
    assert DEFAULT_INPUT_SIZE == 518


def test_png_relative(tmp_path: Path) -> None:
    """PNG input yields RELATIVE depth with no units and no metric claim."""
    backend = _make_backend(tmp_path)
    inspection = inspect_input(make_png(tmp_path / "a.png"))
    result = backend.estimate_depth(inspection)
    assert result.depth_scale is DepthScale.RELATIVE
    assert result.units is None
    assert result.elevation_semantics is ElevationSemantics.RELATIVE_DEPTH
    assert result.georeferencing is GeoreferencingLevel.NON_GEOREFERENCED
    assert result.output_resolution.width == result.input_resolution.width
    assert result.output_resolution.height == result.input_resolution.height
    assert all(v == v for v in result.depth_values)


def test_jpeg_relative(tmp_path: Path) -> None:
    """JPEG input follows the same relative contract."""
    backend = _make_backend(tmp_path)
    inspection = inspect_input(make_jpeg(tmp_path / "a.jpg"))
    result = backend.estimate_depth(inspection)
    assert result.depth_scale is DepthScale.RELATIVE
    assert result.units is None


def test_deterministic_output(tmp_path: Path) -> None:
    """Repeat inference on the same input is byte-identical."""
    backend = _make_backend(tmp_path)
    inspection = inspect_input(make_png(tmp_path / "a.png"))
    first = backend.estimate_depth(inspection)
    second = backend.estimate_depth(inspection)
    assert first.depth_values == second.depth_values


def test_provenance_links_input_and_candidate(tmp_path: Path) -> None:
    """Provenance carries input checksum, M17 identity and lineage."""
    backend = _make_backend(tmp_path)
    inspection = inspect_input(make_png(tmp_path / "a.png"))
    result = backend.estimate_depth(inspection)
    assert result.provenance.input_checksum == inspection.handle.sha256
    assert result.provenance.model_name == "m17-geonrw-struct"
    assert result.provenance.model_version == MODEL_VERSION
    assert result.checkpoint_id is not None and "m17-geonrw-struct-e01" in result.checkpoint_id
    assert result.provenance.software_version == __version__
    assert result.provenance.units is None
    assert "M17" in (result.provenance.semantic_meaning or "")


def test_preprocessing_record_documents_frozen_path(tmp_path: Path) -> None:
    """Preprocessing record pins the frozen M17 path (zstats, grid)."""
    backend = _make_backend(tmp_path)
    inspection = inspect_input(make_png(tmp_path / "a.png"))
    result = backend.estimate_depth(inspection)
    record = result.preprocessing
    assert "zscore" in record["normalize"]
    assert "source grid" in record["output_restore"]
    assert "first-3" in record["input_color"]


def test_missing_checkpoint_raises(tmp_path: Path) -> None:
    """Absent checkpoint fails loudly (never silent, never synthetic)."""
    backend = M17DepthBackend(
        checkpoint=tmp_path / "missing.pt",
        device="cpu",
        model_factory=_FakeM17Model,
    )
    inspection = inspect_input(make_png(tmp_path / "a.png"))
    with pytest.raises(ModelInferenceError, match="checkpoint not found"):
        backend.estimate_depth(inspection)


def test_real_head_unavailable_without_factory(tmp_path: Path) -> None:
    """Without an injected factory the missing head raises explicitly."""
    fake_ckpt = tmp_path / "fake-best.pt"
    fake_ckpt.write_bytes(b"fake-m17-weights")
    backend = M17DepthBackend(checkpoint=fake_ckpt, device="cpu")
    inspection = inspect_input(make_png(tmp_path / "a.png"))
    with pytest.raises(ModelInferenceError, match="head implementation is not available"):
        backend.estimate_depth(inspection)


def test_invalid_device_rejected(tmp_path: Path) -> None:
    """Unknown device names fail at construction."""
    with pytest.raises(ValueError, match="Unknown device"):
        M17DepthBackend(checkpoint=tmp_path / "x.pt", device="tpu")


def test_rejects_non_inspection_input(tmp_path: Path) -> None:
    """Non-inspection inputs are rejected with InvalidInputError."""
    backend = _make_backend(tmp_path)
    with pytest.raises(InvalidInputError):
        backend.estimate_depth(None)  # type: ignore[arg-type]


def test_model_name_is_not_dav2() -> None:
    """M17 identity is distinct from the canonical DA-V2 adapter."""
    assert MODEL_NAME == "M17-GeoNRW-Struct"
    assert MODEL_NAME != "DepthAnythingV2-Small"
