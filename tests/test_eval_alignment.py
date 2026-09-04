"""Evaluation-protocol tests (synthetic; asserts guardrails, not just math)."""

import pytest

np = pytest.importorskip("numpy")

from depthwizard.eval.alignment import (  # noqa: E402
    affine_fit,
    apply_affine,
    build_mask,
    evaluate_sample,
    mae,
    pearson,
    rmse,
    spearman,
)


def test_mask_keeps_negatives_drops_nonfinite():
    pred = np.array([[1.0, float("nan")], [float("inf"), 2.0]])
    tgt = np.array([[-5.0, 1.0], [2.0, float("nan")]])
    m = build_mask(pred, tgt)
    # (-5.0 kept: negatives are NOT masked), nan/inf dropped.
    assert m.tolist() == [[True, False], [False, False]]
    with pytest.raises(ValueError):
        build_mask(np.zeros((2, 2)), np.zeros((3, 3)))


def test_affine_fit_exact_linear():
    pred = np.array([0.0, 1.0, 2.0, 3.0])
    tgt = 2.5 * pred - 1.0
    a, b, deg = affine_fit(pred, tgt)
    assert deg is False
    assert a == pytest.approx(2.5) and b == pytest.approx(-1.0)
    assert apply_affine(pred, a, b) == pytest.approx(tgt)


def test_affine_fit_degenerate_constant_prediction():
    a, b, deg = affine_fit(np.ones(5), np.arange(5.0))
    assert deg is True and a is None and b is None
    a2, b2, deg2 = affine_fit(np.array([1.0]), np.array([2.0]))
    assert deg2 is True


def test_affine_fit_per_image_only_documented():
    # Two images with different scales must NOT share parameters: fit each.
    a1, _, _ = affine_fit(np.array([0.0, 1.0]), np.array([0.0, 10.0]))
    a2, _, _ = affine_fit(np.array([0.0, 1.0]), np.array([0.0, 1.0]))
    assert a1 == pytest.approx(10.0) and a2 == pytest.approx(1.0)


def test_metrics_on_aligned_values():
    aligned = np.array([1.0, 2.0, 3.0])
    tgt = np.array([1.0, 3.0, 2.0])
    m = np.ones(3, bool)
    assert mae(aligned, tgt, m) == pytest.approx(2 / 3)
    assert rmse(aligned, tgt, m) == pytest.approx((2 / 3) ** 0.5)
    assert pearson(aligned, tgt, m) == pytest.approx(0.5)
    assert spearman(aligned, tgt, m) == pytest.approx(0.5)


def test_pearson_spearman_none_on_constant():
    m = np.ones(4, bool)
    assert pearson(np.ones(4), np.arange(4.0), m) is None
    assert spearman(np.ones(4), np.arange(4.0), m) is None


def test_evaluate_sample_no_raw_error_field():
    # Rule F: the report must not contain any raw-prediction-vs-meter error.
    pred = np.array([[0.5, 1.5], [1.0, 2.0]])
    tgt = np.array([[0.0, 10.0], [5.0, 20.0]])
    out = evaluate_sample(pred, tgt)
    assert "raw_mae" not in out and "raw_rmse" not in out
    assert "raw_mae" not in str(out) and "raw_rmse" not in str(out)
    assert out["raw"]["mean"] == pytest.approx(1.25)
    assert out["affine"]["per_image_only"] is True
    assert out["aligned"]["mae"] is not None and out["pearson"] is not None


def test_evaluate_sample_no_target_clipping():
    # Negatives in the TARGET must flow into metrics untouched.
    pred = np.array([0.0, 1.0, 2.0, 3.0])
    tgt = np.array([-5.0, 0.0, 5.0, 10.0])
    out = evaluate_sample(pred, tgt)
    assert out["n_valid"] == 4  # nothing clipped away
    assert out["aligned"]["mae"] == pytest.approx(0.0)  # exact affine fit


def test_evaluate_sample_degenerate_never_nan():
    out = evaluate_sample(np.ones((3, 3)), np.arange(9.0).reshape(3, 3))
    assert out["affine"]["degenerate"] is True
    assert out["aligned"]["mae"] is None
    assert "nan" not in str(out["aligned"]).lower()
