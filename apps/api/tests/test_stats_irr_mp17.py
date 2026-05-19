"""Phase 17 (MP17) — Broader IRR tests."""
from __future__ import annotations

import math

import numpy as np
import pytest

from research_api.services.stats.irr import (
    fleiss_kappa,
    krippendorff_alpha,
    weighted_kappa,
)


# ── Fleiss kappa ────────────────────────────────────────────────────────────


def test_fleiss_kappa_perfect_agreement_returns_one():
    # 10 subjects, 5 raters, 3 categories — every rater chooses category 0.
    matrix = [[5, 0, 0] for _ in range(10)]
    res = fleiss_kappa(matrix)
    assert math.isclose(res["kappa"], 1.0, abs_tol=1e-9)
    assert res["n_subjects"] == 10
    assert res["n_raters"] == 5
    assert res["n_categories"] == 3


def test_fleiss_kappa_random_chance_near_zero():
    rng = np.random.default_rng(0)
    n_subj, n_rat, n_cat = 200, 10, 3
    matrix = np.zeros((n_subj, n_cat), dtype=int)
    for i in range(n_subj):
        choices = rng.integers(0, n_cat, n_rat)
        for c in choices:
            matrix[i, c] += 1
    res = fleiss_kappa(matrix.tolist())
    # With random ratings, expect kappa ~ 0.
    assert abs(res["kappa"]) < 0.1


def test_fleiss_kappa_validates_dimensions():
    with pytest.raises(ValueError, match="2-D"):
        fleiss_kappa([1, 2, 3])  # type: ignore[arg-type]


def test_fleiss_kappa_requires_uniform_raters_per_subject():
    with pytest.raises(ValueError, match="same number"):
        fleiss_kappa([[5, 0, 0], [3, 1, 0]])  # 5 raters vs 4 raters


# ── Krippendorff alpha ──────────────────────────────────────────────────────


def test_krippendorff_nominal_perfect_agreement():
    """Two raters, 5 items, identical ratings → α = 1."""
    ratings = [
        [1.0, 2.0, 3.0, 4.0, 5.0],
        [1.0, 2.0, 3.0, 4.0, 5.0],
    ]
    res = krippendorff_alpha(np.array(ratings), level="nominal")
    assert math.isclose(res["alpha"], 1.0, abs_tol=1e-9)


def test_krippendorff_nominal_total_disagreement():
    """Two raters who disagree on every item → α < 0."""
    ratings = [
        [1.0, 2.0, 3.0, 4.0],
        [4.0, 3.0, 2.0, 1.0],
    ]
    res = krippendorff_alpha(np.array(ratings), level="nominal")
    assert res["alpha"] < 0.0


def test_krippendorff_interval_higher_than_nominal_for_close_values():
    """For numerically close ratings, interval α >= nominal α."""
    ratings = [
        [1.0, 2.0, 3.0, 4.0],
        [1.0, 2.1, 3.1, 4.0],
    ]
    nominal = krippendorff_alpha(np.array(ratings), level="nominal")
    interval = krippendorff_alpha(np.array(ratings), level="interval")
    # Interval treats 2.0 vs 2.1 as nearly identical, so much higher α.
    assert interval["alpha"] > nominal["alpha"]


def test_krippendorff_handles_missing_ratings():
    arr = np.array(
        [
            [1.0, 2.0, np.nan, 4.0],
            [1.0, 2.0, 3.0, 4.0],
        ]
    )
    res = krippendorff_alpha(arr, level="nominal")
    # 3 pairable items (the 3rd has only 1 obs).
    assert res["n_pairable"] == 6  # 1 item has 1 obs (skipped); 3 items have 2 obs = 6


def test_krippendorff_validates_raters():
    with pytest.raises(ValueError, match=">= 2 raters"):
        krippendorff_alpha(np.array([[1.0, 2.0, 3.0]]), level="nominal")


# ── Weighted kappa ──────────────────────────────────────────────────────────


def test_weighted_kappa_linear_perfect_agreement():
    r1 = [0, 1, 2, 3]
    r2 = [0, 1, 2, 3]
    res = weighted_kappa(r1, r2, weights="linear")
    assert math.isclose(res["kappa"], 1.0, abs_tol=1e-9)


def test_weighted_kappa_quadratic_more_lenient_on_adjacent_disagreements():
    """One-off disagreement on an ordinal scale: quadratic kappa >= linear kappa."""
    r1 = [0, 1, 2, 3, 4]
    r2 = [0, 1, 3, 3, 4]  # one disagreement (2 vs 3)
    linear = weighted_kappa(r1, r2, weights="linear")
    quadratic = weighted_kappa(r1, r2, weights="quadratic")
    assert quadratic["kappa"] >= linear["kappa"]


def test_weighted_kappa_bootstrap_ci():
    rng = np.random.default_rng(0)
    n = 80
    r1 = rng.integers(0, 4, n)
    r2 = r1.copy()
    # Add 20% disagreement
    flip_mask = rng.random(n) < 0.2
    r2 = np.where(flip_mask, (r2 + 1) % 4, r2)
    res = weighted_kappa(r1, r2, weights="linear", n_bootstrap=100, seed=42)
    assert res["ci_low"] is not None and res["ci_high"] is not None
    assert res["ci_low"] <= res["kappa"] <= res["ci_high"]
    assert res["se"] is not None and res["se"] >= 0


def test_weighted_kappa_validates_weights():
    with pytest.raises(ValueError, match="weights must be"):
        weighted_kappa([0, 1], [0, 1], weights="bogus")  # type: ignore[arg-type]


def test_weighted_kappa_validates_shapes():
    with pytest.raises(ValueError, match="same shape"):
        weighted_kappa([0, 1], [0, 1, 2], weights="linear")
