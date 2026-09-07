"""Terrain-stratified benchmark evaluation tests."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from depthwizard.contracts.artifacts import DepthResult, ImageResolution
from depthwizard.contracts.provenance import ProductProvenance
from depthwizard.contracts.semantics import (
    DepthScale,
    ElevationSemantics,
)
from depthwizard.contracts.spatial import SpatialContext, SpatialKind
from depthwizard.evaluation.datasets import (
    BenchmarkSample,
    LoadedSample,
    ReferenceInfo,
    TerrainClass,
    TerrainStratifiedDataset,
)
from depthwizard.evaluation.results import StratifiedEvaluationResult
from depthwizard.evaluation.runner import run_stratified_evaluation
from depthwizard.ingestion.models import InputInspection
from depthwizard.version import __version__


class StratifiedSmokeBackend:
    """Test-only backend emitting an exact affine relative pattern at any resolution."""

    model_name = "stratified-smoke"
    model_version: str | None = "0.0.0"
    checkpoint_id: str | None = None

    def estimate_depth(self, inspection: InputInspection) -> DepthResult:
        h, w = inspection.height, inspection.width
        grid = np.arange(h * w, dtype=np.float64).reshape(h, w)
        relative = (grid - 10.0) / 2.5
        flat = tuple(float(v) for v in relative.ravel())
        resolution = ImageResolution(width=w, height=h)
        return DepthResult(
            model_name=self.model_name,
            model_version=self.model_version,
            checkpoint_id=self.checkpoint_id,
            input_resolution=resolution,
            output_resolution=resolution,
            depth_scale=DepthScale.RELATIVE,
            elevation_semantics=ElevationSemantics.RELATIVE_DEPTH,
            georeferencing=inspection.georeferencing,
            depth_values=flat,
            preprocessing={"stratified": "synthetic-affine"},
            units=None,
            spatial=SpatialContext(kind=SpatialKind.NOT_APPLICABLE),
            provenance=ProductProvenance(
                source_input_id=inspection.handle.display_name,
                input_checksum=inspection.handle.sha256,
                model_name=self.model_name,
                model_version=self.model_version,
                checkpoint_id=None,
                software_version=__version__,
                generated_at=None,
                units=None,
                semantic_meaning="stratified smoke fixture",
            ),
        )


def _synthetic_loader(sample: BenchmarkSample) -> LoadedSample:
    h, w = sample.height, sample.width
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    for row in range(h):
        for col in range(w):
            value = 255 if (row + col) % 2 == 0 else 0
            rgb[row, col] = (value, (col * 32) % 256, (row * 40) % 256)
    reference = np.arange(h * w, dtype=np.float64).reshape(h, w)
    return LoadedSample(
        sample=sample,
        image_rgb=np.ascontiguousarray(rgb),
        reference=ReferenceInfo(
            values=np.ascontiguousarray(reference),
            width=w,
            height=h,
            units="meters",
            semantics=ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
            crs=sample.crs,
            valid_mask=np.ones_like(reference, dtype=bool),
        ),
    )


def test_terrain_class_enum_values() -> None:
    assert TerrainClass.URBAN == "urban"
    assert TerrainClass.HILLY == "hilly"
    assert TerrainClass.FORESTED == "forested"
    assert TerrainClass.SPARSE == "sparse"
    assert TerrainClass.WATER == "water"
    assert set(TerrainClass._value2member_map_) == {"urban", "hilly", "forested", "sparse", "water"}


def test_benchmark_sample_validation() -> None:
    sample = BenchmarkSample(
        sample_id="test-001",
        input_path="test/input.png",
        terrain_class=TerrainClass.URBAN,
        width=4,
        height=4,
    )
    assert sample.sample_id == "test-001"
    assert sample.terrain_class is TerrainClass.URBAN
    assert sample.city is None
    assert sample.metadata == {}
    assert sample.width == 4


def test_benchmark_sample_frozen() -> None:
    sample = BenchmarkSample(
        sample_id="test-002",
        input_path="test/input.png",
        terrain_class=TerrainClass.HILLY,
        width=4,
        height=4,
    )
    with pytest.raises(ValueError):
        sample.sample_id = "changed"


def test_stratified_dataset_from_manifest(tmp_path: Path) -> None:
    manifest = [
        {
            "sample_id": "s1",
            "input_path": "s1.png",
            "terrain_class": "urban",
            "width": 4,
            "height": 4,
        },
        {
            "sample_id": "s2",
            "input_path": "s2.png",
            "terrain_class": "hilly",
            "width": 4,
            "height": 4,
        },
    ]
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    dataset = TerrainStratifiedDataset.from_manifest_path(manifest_path, _synthetic_loader)
    assert len(dataset) == 2
    assert dataset[0].sample_id == "s1"
    assert dataset[1].sample_id == "s2"


def test_stratified_dataset_filter_by_terrain() -> None:
    samples = [
        BenchmarkSample(
            sample_id="u1", input_path="u1.png", terrain_class=TerrainClass.URBAN, width=4, height=4
        ),
        BenchmarkSample(
            sample_id="h1", input_path="h1.png", terrain_class=TerrainClass.HILLY, width=4, height=4
        ),
        BenchmarkSample(
            sample_id="u2", input_path="u2.png", terrain_class=TerrainClass.URBAN, width=4, height=4
        ),
    ]
    dataset = TerrainStratifiedDataset(samples, _synthetic_loader)
    urban = dataset.filter_by_terrain(TerrainClass.URBAN)
    assert len(urban) == 2
    assert urban[0].sample_id == "u1"
    assert urban[1].sample_id == "u2"


def test_stratified_dataset_filter_by_city() -> None:
    samples = [
        BenchmarkSample(
            sample_id="m1",
            input_path="m1.png",
            terrain_class=TerrainClass.URBAN,
            city="Metropolis",
            width=4,
            height=4,
        ),
        BenchmarkSample(
            sample_id="h1",
            input_path="h1.png",
            terrain_class=TerrainClass.HILLY,
            city="Highland",
            width=4,
            height=4,
        ),
        BenchmarkSample(
            sample_id="m2",
            input_path="m2.png",
            terrain_class=TerrainClass.URBAN,
            city="Metropolis",
            width=4,
            height=4,
        ),
    ]
    dataset = TerrainStratifiedDataset(samples, _synthetic_loader)
    metro = dataset.filter_by_city("Metropolis")
    assert len(metro) == 2
    assert all(s.city == "Metropolis" for s in [metro[i] for i in range(len(metro))])


def test_run_stratified_evaluation_returns_per_class_metrics() -> None:
    samples = [
        BenchmarkSample(
            sample_id="urban-001",
            input_path="u1.png",
            terrain_class=TerrainClass.URBAN,
            width=4,
            height=4,
        ),
        BenchmarkSample(
            sample_id="hilly-001",
            input_path="h1.png",
            terrain_class=TerrainClass.HILLY,
            width=4,
            height=4,
        ),
        BenchmarkSample(
            sample_id="forested-001",
            input_path="f1.png",
            terrain_class=TerrainClass.FORESTED,
            width=4,
            height=4,
        ),
    ]
    dataset = TerrainStratifiedDataset(samples, _synthetic_loader)
    results = run_stratified_evaluation(dataset, StratifiedSmokeBackend())
    assert set(results.keys()) == {"urban", "hilly", "forested"}
    for metrics in results.values():
        assert "mae" in metrics
        assert "rmse" in metrics
        assert "r_squared" in metrics
        assert "count" in metrics
        assert metrics["count"] == 1.0


def test_run_stratified_evaluation_max_samples() -> None:
    samples = [
        BenchmarkSample(
            sample_id="urban-001",
            input_path="u1.png",
            terrain_class=TerrainClass.URBAN,
            width=4,
            height=4,
        ),
        BenchmarkSample(
            sample_id="urban-002",
            input_path="u2.png",
            terrain_class=TerrainClass.URBAN,
            width=4,
            height=4,
        ),
        BenchmarkSample(
            sample_id="hilly-001",
            input_path="h1.png",
            terrain_class=TerrainClass.HILLY,
            width=4,
            height=4,
        ),
        BenchmarkSample(
            sample_id="hilly-002",
            input_path="h2.png",
            terrain_class=TerrainClass.HILLY,
            width=4,
            height=4,
        ),
        BenchmarkSample(
            sample_id="forested-001",
            input_path="f1.png",
            terrain_class=TerrainClass.FORESTED,
            width=4,
            height=4,
        ),
        BenchmarkSample(
            sample_id="forested-002",
            input_path="f2.png",
            terrain_class=TerrainClass.FORESTED,
            width=4,
            height=4,
        ),
    ]
    dataset = TerrainStratifiedDataset(samples, _synthetic_loader)
    results = run_stratified_evaluation(dataset, StratifiedSmokeBackend(), max_samples=1)
    for metrics in results.values():
        assert metrics["count"] == 1.0


def test_run_stratified_evaluation_deterministic_selection() -> None:
    samples = [
        BenchmarkSample(
            sample_id="b-urban",
            input_path="b.png",
            terrain_class=TerrainClass.URBAN,
            width=4,
            height=4,
        ),
        BenchmarkSample(
            sample_id="a-urban",
            input_path="a.png",
            terrain_class=TerrainClass.URBAN,
            width=4,
            height=4,
        ),
    ]
    dataset = TerrainStratifiedDataset(samples, _synthetic_loader)
    results = run_stratified_evaluation(dataset, StratifiedSmokeBackend(), max_samples=1)
    assert results["urban"]["count"] == 1.0


def test_stratified_evaluation_result_serialization() -> None:
    result = StratifiedEvaluationResult(
        overall={"mae": 0.1, "rmse": 0.2, "r_squared": 0.9},
        by_terrain_class={
            "urban": {"mae": 0.1, "rmse": 0.2, "r_squared": 0.9, "count": 2.0},
            "hilly": {"mae": 0.3, "rmse": 0.4, "r_squared": 0.7, "count": 1.0},
        },
        total_samples=3,
        valid_samples=3,
        backend_name="test-backend",
        backend_version="1.0",
        calibration_method="control-stride",
        engine_version="1.0.0",
    )
    text = result.model_dump_json()
    loaded = json.loads(text)
    assert loaded["backend_name"] == "test-backend"
    assert loaded["total_samples"] == 3
    assert loaded["by_terrain_class"]["urban"]["count"] == 2.0


def test_stratified_evaluation_result_to_json_path(tmp_path: Path) -> None:
    result = StratifiedEvaluationResult(
        overall={"mae": 0.1, "rmse": 0.2, "r_squared": 0.9},
        by_terrain_class={"urban": {"mae": 0.1, "rmse": 0.2, "r_squared": 0.9, "count": 1.0}},
        total_samples=1,
        valid_samples=1,
        backend_name="test-backend",
        backend_version=None,
        calibration_method=None,
        engine_version="1.0.0",
    )
    out_path = tmp_path / "result.json"
    result.to_json_path(out_path)
    assert out_path.exists()
    loaded = json.loads(out_path.read_text(encoding="utf-8"))
    assert loaded["valid_samples"] == 1
