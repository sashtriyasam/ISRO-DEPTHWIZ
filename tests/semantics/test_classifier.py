"""Basic tests for RuleBasedTerrainClassifier and SemanticMask."""

import numpy as np
import pytest
from pydantic import ValidationError

from depthwizard.semantics.classifier import (
    LandCoverClass,
    RuleBasedTerrainClassifier,
    SemanticMask,
    TerrainClassifier,
)


def _rgb(h, w):
    rng = np.random.default_rng(0)
    return rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)


def test_classifier_protocol_has_classify():
    assert hasattr(TerrainClassifier, "classify")


def test_land_cover_class_values():
    assert LandCoverClass.UNKNOWN == 0
    assert LandCoverClass.BUILDING == 1
    assert LandCoverClass.ROAD == 2
    assert LandCoverClass.BARE_SOIL == 3
    assert LandCoverClass.VEGETATION == 4
    assert LandCoverClass.WATER == 5
    assert LandCoverClass.SHADOW == 6


def test_rule_based_classifier_output_shape():
    rgb = _rgb(16, 16)
    clf = RuleBasedTerrainClassifier()
    result = clf.classify(rgb)
    assert result.shape == (16, 16)
    assert result.dtype == np.int16


def test_rule_based_classifier_valid_classes():
    rgb = _rgb(16, 16)
    clf = RuleBasedTerrainClassifier()
    result = clf.classify(rgb)
    unique = set(result.ravel().tolist())
    assert unique.issubset({c.value for c in LandCoverClass})


def test_semantic_mask_model():
    class_map = np.full((4, 4), LandCoverClass.BUILDING, dtype=np.int16)
    mask = SemanticMask(class_map=class_map, method="test")
    assert mask.class_map.shape == (4, 4)
    assert mask.method == "test"
    assert mask.class_names[1] == "BUILDING"


def test_semantic_mask_frozen():
    class_map = np.full((4, 4), LandCoverClass.BUILDING, dtype=np.int16)
    mask = SemanticMask(class_map=class_map, method="test")
    with pytest.raises(ValidationError):
        mask.class_map = np.zeros((2, 2), dtype=np.int16)


def test_classifier_rejects_bad_input():
    clf = RuleBasedTerrainClassifier()
    try:
        clf.classify(np.zeros((4, 4), dtype=np.uint8))
        raise AssertionError("Should reject 2D input")
    except ValueError:
        pass
    try:
        clf.classify(np.zeros((4, 4, 4), dtype=np.uint8))
        raise AssertionError("Should reject 4-channel input")
    except ValueError:
        pass
