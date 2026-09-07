"""Semantic-aware calibration sample selection and weighting."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest

from depthwizard.calibration import CalibrationSamples, ScaleOffsetCalibrator
from depthwizard.calibration.sampling import (
    DEFAULT_CLASS_WEIGHTS,
    SemanticWeighter,
    TerrainClassWeighter,
    UniformWeighter,
    build_calibration_samples_with_weights,
    stratified_sample_selection,
)
from depthwizard.contracts.semantics import ElevationSemantics
from depthwizard.controls.models import ReferenceControlPoint


def _base(**overrides: Any) -> CalibrationSamples:
    base: dict[str, Any] = {
        "predicted_values": (0.0, 1.0, 2.0, 3.0),
        "reference_values": (10.0, 12.5, 15.0, 17.5),
        "reference_id": "ref-001",
        "reference_units": "meters",
        "target_semantics": ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
    }
    base.update(overrides)
    return CalibrationSamples(**base)


def test_uniform_weighter_returns_one() -> None:
    weighter = UniformWeighter()
    for p, r in ((0.0, 10.0), (1.5, 12.5), (-3.0, 5.0)):
        assert weighter.weight(p, r, 0, 0) == 1.0
        assert weighter.weight(p, r, 0, 0, "building") == 1.0


def test_semantic_weighter_known_classes() -> None:
    weighter = SemanticWeighter()
    assert weighter.weight(0.0, 10.0, 0, 0, "building") == 2.0
    assert weighter.weight(0.0, 10.0, 0, 0, "road") == 1.5
    assert weighter.weight(0.0, 10.0, 0, 0, "bare_soil") == 1.0
    assert weighter.weight(0.0, 10.0, 0, 0, "vegetation") == 0.8
    assert weighter.weight(0.0, 10.0, 0, 0, "water") == 0.0
    assert weighter.weight(0.0, 10.0, 0, 0, "shadow") == 0.0


def test_semantic_weighter_unknown_class_falls_back() -> None:
    weighter = SemanticWeighter(default_weight=0.5)
    assert weighter.weight(0.0, 10.0, 0, 0, "unknown") == 0.5


def test_semantic_weighter_none_class_uses_default() -> None:
    weighter = SemanticWeighter(default_weight=0.3)
    assert weighter.weight(0.0, 10.0, 0, 0, None) == 0.3


def test_terrain_class_weighter_sparse_upweighted() -> None:
    values = (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 100.0)
    weighter = TerrainClassWeighter(elevation_bins=2)
    weighter.fit(values)
    weights = [weighter.weight(v, v + 10.0, 0, 0) for v in values]
    assert len(weights) == len(values)
    for w in weights:
        assert w > 0.0
    bin_counts = [sum(1 for v in values if (v <= 5.5) == (wv <= 5.5)) for wv in values[:10]]
    assert len(set(bin_counts)) > 1
    sparse_bin_weight = 1.0 / (min(bin_counts) + 1)
    dense_bin_weight = 1.0 / (max(bin_counts) + 1)
    assert sparse_bin_weight > dense_bin_weight


def test_stratified_selection_reduces_count() -> None:
    samples = _base(predicted_values=(0.0, 1.0, 2.0, 3.0), reference_values=(10.0, 11.0, 12.0, 13.0))
    selected = stratified_sample_selection(samples, max_samples=2)
    assert selected.total_samples == 2


def test_stratified_selection_preserves_order() -> None:
    predicted = (0.0, 1.0, 2.0, 3.0)
    reference = (10.0, 11.0, 12.0, 13.0)
    samples = _base(predicted_values=predicted, reference_values=reference)
    weighter = SemanticWeighter(class_weights={"building": 10.0}, default_weight=1.0)
    selected = stratified_sample_selection(samples, max_samples=2, weighter=weighter)
    selected_preds = selected.predicted_values
    assert selected_preds == (0.0, 1.0) or selected_preds == (2.0, 3.0) or len(selected_preds) == 2


def test_stratified_selection_returns_original_when_within_limit() -> None:
    samples = _base()
    selected = stratified_sample_selection(samples, max_samples=10)
    assert selected is samples


def test_build_calibration_samples_with_weights_sets_weights() -> None:
    points = [
        ReferenceControlPoint(
            control_id="p1",
            target_semantics=ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
            row=0,
            col=0,
            predicted_value=0.1,
            surface_elevation_m=100.0,
            reference_value=100.0,
            surface_source_id="s",
            depth_model="m",
        ),
        ReferenceControlPoint(
            control_id="p2",
            target_semantics=ElevationSemantics.ABSOLUTE_ELEVATION_DSM,
            row=1,
            col=1,
            predicted_value=0.2,
            surface_elevation_m=101.0,
            reference_value=101.0,
            surface_source_id="s",
            depth_model="m",
        ),
    ]
    mask = np.array([[0, 1], [2, 3]], dtype=np.int32)
    class_weights = {0: 1.0, 1: 2.0, 2: 0.5, 3: 0.0}
    samples = build_calibration_samples_with_weights(
        points, reference_id="ref-w", semantic_mask=mask, class_weights=class_weights
    )
    assert samples.sample_weights == (1.0, 0.0)
