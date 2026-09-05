"""Significance layer: determinism, schema, power flags, pixel refusal."""

from __future__ import annotations

import numpy as np
import pytest

from depthwizard.evaluation.significance import (
    bootstrap_mean_interval,
    compare_groups,
)


def test_bootstrap_deterministic() -> None:
    """Same seed twice yields identical intervals."""
    values = np.array([3.0, 5.0, 4.0, 6.0, 3.5, 5.5, 4.5, 6.5])
    first = bootstrap_mean_interval(values, "DC", "mae", seed=26175, resamples=500)
    second = bootstrap_mean_interval(values, "DC", "mae", seed=26175, resamples=500)
    assert first == second
    assert first.observed_mean == pytest.approx(4.75)
    assert first.ci_low <= first.observed_mean <= first.ci_high


def test_bootstrap_schema() -> None:
    """Intervals carry method, seed, counts, and power flag."""
    values = np.arange(1.0, 13.0)
    interval = bootstrap_mean_interval(values, "PHL", "mae", seed=7, resamples=200)
    document = interval.model_dump(mode="json")
    assert document["method"] == "sample-bootstrap"
    assert document["seed"] == 7
    assert document["n"] == 12
    assert document["resamples"] == 200
    assert set(document) == {
        "metric",
        "group",
        "n",
        "observed_mean",
        "ci_low",
        "ci_high",
        "confidence",
        "resamples",
        "seed",
        "method",
        "adequately_powered",
        "note",
    }


def test_underpowered_flagged_descriptive() -> None:
    """Small groups are labelled descriptive-only, never inferential."""
    interval = bootstrap_mean_interval(np.array([1.0, 2.0, 3.0]), "DC", "mae")
    assert interval.adequately_powered is False
    assert "descriptive only" in interval.note
    assert "underpowered" in interval.note


def test_powered_group_inferential() -> None:
    """Groups meeting the minimum are not flagged."""
    values = np.linspace(1.0, 5.0, 12)
    interval = bootstrap_mean_interval(values, "DC", "mae")
    assert interval.adequately_powered is True
    assert interval.note == "inferential interval"


def test_group_comparison_arithmetic() -> None:
    """Delta, counts, and interval ordering are exact."""
    group_a = np.array([9.0, 9.5, 8.5, 9.2, 8.8, 9.1, 9.4, 8.9])
    group_b = np.array([3.0, 3.2, 2.8, 3.1, 2.9, 3.3, 3.0, 3.2])
    comparison = compare_groups(group_a, group_b, "DC", "PHL", "mae", seed=26175, resamples=500)
    assert comparison.observed_delta == pytest.approx(np.mean(group_a) - np.mean(group_b))
    assert comparison.n_a == 8 and comparison.n_b == 8
    assert comparison.ci_low <= comparison.observed_delta <= comparison.ci_high
    assert comparison.ci_low > 0  # clearly separated fixture groups
    assert comparison.adequately_powered is False  # n=8 < 10: honest flag
    assert comparison.method == "two-sample-bootstrap"


def test_comparison_deterministic() -> None:
    """Same seed twice yields identical comparisons."""
    group_a = np.array([1.0, 2.0, 3.0, 4.0])
    group_b = np.array([2.0, 3.0, 4.0, 5.0])
    first = compare_groups(group_a, group_b, "A", "B", "mae", seed=99, resamples=300)
    second = compare_groups(group_a, group_b, "A", "B", "mae", seed=99, resamples=300)
    assert first == second


def test_empty_group_refused() -> None:
    """Empty groups raise instead of returning vacuous intervals."""
    with pytest.raises(ValueError, match="EVALUATION_FAILED"):
        bootstrap_mean_interval(np.array([]), "DC", "mae")
    with pytest.raises(ValueError, match="EVALUATION_FAILED"):
        compare_groups(np.array([]), np.array([1.0]), "A", "B", "mae")


def test_nonfinite_refused() -> None:
    """NaN metric values are refused, never bootstrapped."""
    with pytest.raises(ValueError, match="EVALUATION_FAILED"):
        bootstrap_mean_interval(np.array([1.0, float("nan")]), "DC", "mae")
