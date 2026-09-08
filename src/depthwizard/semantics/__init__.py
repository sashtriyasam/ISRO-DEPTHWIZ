"""Semantic classification, depth refinement, and SAM adapter stubs."""

from depthwizard.semantics.classifier import (
    LandCoverClass,
    RuleBasedTerrainClassifier,
    SemanticMask,
    TerrainClassifier,
)
from depthwizard.semantics.refine import refine_depth_map
from depthwizard.semantics.sam_adapter import (
    BuildingRANSACRefiner,
    EdgeAwareBilateralRefiner,
    SAMRefiner,
)

__all__ = [
    "LandCoverClass",
    "TerrainClassifier",
    "RuleBasedTerrainClassifier",
    "SemanticMask",
    "refine_depth_map",
    "SAMRefiner",
    "EdgeAwareBilateralRefiner",
    "BuildingRANSACRefiner",
]
