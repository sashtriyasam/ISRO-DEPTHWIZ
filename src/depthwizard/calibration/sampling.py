"""Semantic-aware calibration sample selection and weighting.

Provides weighters that bias sample selection toward informative
regions (buildings, roads, sparse terrain) and away from ambiguous
or excluded classes (water, shadow). Selection is deterministic and
order-preserving.
"""

from __future__ import annotations

import math
from typing import Protocol

import numpy as np

from depthwizard.calibration.models import CalibrationSamples
from depthwizard.controls.build import build_calibration_samples
from depthwizard.controls.models import ReferenceControlPoint


class SampleWeighter(Protocol):
    """Interface for per-sample weighting."""

    def weight(
        self,
        predicted: float,
        reference: float,
        row: int,
        col: int,
        semantic_class: str | None = None,
    ) -> float:
        """Return a non-negative weight for a calibration sample.

        Higher weight means the sample is more likely to be selected.
        """
        ...


class UniformWeighter:
    """Uniform weighting: every sample receives weight 1.0."""

    def weight(
        self,
        predicted: float,
        reference: float,
        row: int,
        col: int,
        semantic_class: str | None = None,
    ) -> float:
        return 1.0


DEFAULT_CLASS_WEIGHTS = {
    "building": 2.0,
    "road": 1.5,
    "bare_soil": 1.0,
    "vegetation": 0.8,
    "water": 0.0,
    "shadow": 0.0,
}


class SemanticWeighter:
    """Weight samples by semantic class name.

    Classes absent from ``class_weights`` receive ``default_weight``.
    Recommended defaults downweight or exclude water and shadow.
    """

    def __init__(
        self,
        class_weights: dict[str, float] | None = None,
        default_weight: float = 1.0,
    ) -> None:
        self.class_weights = class_weights if class_weights is not None else dict(DEFAULT_CLASS_WEIGHTS)
        self.default_weight = default_weight

    def weight(
        self,
        predicted: float,
        reference: float,
        row: int,
        col: int,
        semantic_class: str | None = None,
    ) -> float:
        if semantic_class is not None:
            return self.class_weights.get(semantic_class, self.default_weight)
        return self.default_weight


class TerrainClassWeighter:
    """Upweight sparse regions based on local prediction density.

    Quantile-bins the ``predicted_values`` into ``elevation_bins``
    groups and assigns weight ``1.0 / (count_in_bin + 1)`` so that
    bins with fewer samples receive higher weight.
    """

    def __init__(self, elevation_bins: int = 5) -> None:
        self.elevation_bins = elevation_bins
        self._bin_counts: dict[int, int] = {}
        self._fitted = False

    def fit(self, predicted_values: tuple[float, ...]) -> None:
        if len(predicted_values) == 0:
            self._bin_counts = {}
            self._fitted = True
            return
        arr = np.asarray(predicted_values, dtype=np.float64)
        if self.elevation_bins <= 0 or self.elevation_bins > len(arr):
            bins = np.zeros(len(arr), dtype=np.int64)
        else:
            quantiles = np.quantile(arr, np.linspace(0.0, 1.0, self.elevation_bins + 1))
            bins = np.digitize(arr, quantiles[1:-1], right=False)
            bins = np.clip(bins, 0, self.elevation_bins - 1)
        counts: dict[int, int] = {}
        for b in bins.tolist():
            counts[b] = counts.get(b, 0) + 1
        self._bin_counts = counts
        self._fitted = True

    def weight(
        self,
        predicted: float,
        reference: float,
        row: int,
        col: int,
        semantic_class: str | None = None,
    ) -> float:
        if not self._fitted:
            raise RuntimeError("TerrainClassWeighter must be fit before weighting samples")
        arr = np.asarray((predicted,), dtype=np.float64)
        if self.elevation_bins <= 0 or self.elevation_bins > 1:
            bins = np.zeros(1, dtype=np.int64)
        else:
            quantiles = np.quantile(
                np.asarray(tuple(self._bin_counts.keys()), dtype=np.float64) if self._bin_counts else np.array([0.0]),
                np.linspace(0.0, 1.0, self.elevation_bins + 1),
            )
            bins = np.digitize(arr, quantiles[1:-1], right=False)
            bins = np.clip(bins, 0, self.elevation_bins - 1)
        bin_id = int(bins[0])
        count = self._bin_counts.get(bin_id, 0)
        return 1.0 / (count + 1)


def stratified_sample_selection(
    samples: CalibrationSamples,
    max_samples: int,
    weighter: SampleWeighter | None = None,
    seed: int = 0,
) -> CalibrationSamples:
    """Select up to ``max_samples`` samples using deterministic weighting.

    If the sample set is already within the limit, returns it unchanged.
    Otherwise computes per-sample weights, sorts by weight descending,
    takes the top ``max_samples``, and preserves their original order
    in the returned ``CalibrationSamples``.
    """
    if samples.total_samples <= max_samples:
        return samples
    if weighter is None:
        weighter = UniformWeighter()
    predicted = samples.predicted_values
    reference = samples.reference_values
    rows = [0] * samples.total_samples
    cols = list(range(samples.total_samples))
    weights = [
        weighter.weight(p, r, row, col)
        for row, (p, r, col) in enumerate(zip(predicted, reference, cols, strict=True))
    ]
    total = math.fsum(weights)
    if total <= 0.0:
        normalized = [1.0 / len(weights)] * len(weights)
    else:
        normalized = [w / total for w in weights]
    indexed = list(enumerate(normalized))
    indexed.sort(key=lambda x: (-x[1], x[0]))
    selected_indices = sorted(idx for idx, _ in indexed[:max_samples])
    new_predicted = tuple(predicted[i] for i in selected_indices)
    new_reference = tuple(reference[i] for i in selected_indices)
    new_valid_mask = None
    if samples.valid_mask is not None:
        new_valid_mask = tuple(samples.valid_mask[i] for i in selected_indices)
    new_weights = None
    if samples.sample_weights is not None:
        new_weights = tuple(samples.sample_weights[i] for i in selected_indices)
    return CalibrationSamples(
        predicted_values=new_predicted,
        reference_values=new_reference,
        valid_mask=new_valid_mask,
        reference_id=samples.reference_id,
        reference_checksum=samples.reference_checksum,
        reference_units=samples.reference_units,
        target_semantics=samples.target_semantics,
        source_input_id=samples.source_input_id,
        source_checksum=samples.source_checksum,
        sample_weights=new_weights,
    )


def build_calibration_samples_with_weights(
    points: Sequence[ReferenceControlPoint],
    *,
    reference_id: str,
    semantic_mask: np.ndarray | None = None,
    class_weights: dict[int, float] | None = None,
    default_weight: float = 1.0,
) -> CalibrationSamples:
    """Build ``CalibrationSamples`` with optional semantic class weights.

    If ``semantic_mask`` is provided, it is an HxW array of class
    indices. For each control point, the class at ``(row, col)`` is
    looked up and mapped through ``class_weights`` (index-based).
    """
    base = build_calibration_samples(points, reference_id=reference_id)
    if semantic_mask is None or class_weights is None or len(class_weights) == 0:
        return base.model_copy(update={"sample_weights": None})
    mask = np.asarray(semantic_mask)
    if mask.ndim != 2:
        raise ValueError(f"semantic_mask must be 2D, got shape {mask.shape}")
    weights = []
    for point in points:
        row = int(point.row)
        col = int(point.col)
        if row < 0 or row >= mask.shape[0] or col < 0 or col >= mask.shape[1]:
            raise IndexError(
                f"control point ({row}, {col}) is outside semantic_mask shape {mask.shape}"
            )
        class_idx = int(mask[row, col])
        weights.append(float(class_weights.get(class_idx, default_weight)))
    return base.model_copy(update={"sample_weights": tuple(weights)})
