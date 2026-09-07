"""Semantic preprocessor pipeline (classification + refinement)."""

from __future__ import annotations

import numpy as np

from depthwizard.ingestion.models import InputInspection
from depthwizard.semantics.classifier import (
    RuleBasedTerrainClassifier,
    SemanticMask,
    TerrainClassifier,
)
from depthwizard.semantics.sam_adapter import SAMRefiner


class SemanticPreprocessor:
    """Coordinate land-cover classification and depth refinement.

    Holds a ``TerrainClassifier`` and optional ``SAMRefiner``.
    The primary entry point is :meth:`process`, which returns a
    refined depth map and a ``SemanticMask``.
    """

    def __init__(
        self,
        classifier: TerrainClassifier | None = None,
        refiner: SAMRefiner | None = None,
    ) -> None:
        self.classifier = classifier if classifier is not None else RuleBasedTerrainClassifier()
        self.refiner = refiner

    @property
    def name(self) -> str:
        """Preprocessor name for run metadata."""
        return "semantic_preprocessor"

    def prepare(self, inspection: InputInspection) -> InputInspection:
        """Return the inspection unchanged (semantic work happens on raster data)."""
        return inspection

    def process(
        self,
        rgb: np.ndarray,
        depth: np.ndarray,
    ) -> tuple[np.ndarray, SemanticMask]:
        """Classify RGB and optionally refine depth.

        Parameters
        ----------
        rgb:
            HxWx3 uint8 RGB image.
        depth:
            HxW float32/float64 depth map.

        Returns
        -------
        tuple[np.ndarray, SemanticMask]
            Refined depth and semantic classification result.
        """
        class_map = self.classifier.classify(rgb)
        mask = SemanticMask(
            class_map=class_map,
            method=type(self.classifier).__name__,
        )

        refined = depth
        if self.refiner is not None:
            refined = self.refiner.refine_depth(rgb, depth, semantic_mask=class_map)

        return refined, mask
