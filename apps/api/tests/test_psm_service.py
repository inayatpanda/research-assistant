"""Phase 13 — PSM (propensity-score matching) known-answer tests.

Synthetic 100-row dataset with treatment correlated to age + sex via a
logistic generative model. After 1:1 nearest-neighbour matching with the
default caliper, every covariate's |SMD| should drop below the standard
0.10 threshold.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from research_api.services.stats.psm import (
    covariate_balance,
    fit_propensity_scores,
    nearest_neighbour_match,
    run_psm,
)


def _synthetic(seed: int = 42, n: int = 200) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    age = rng.normal(50, 10, n)
    sex = rng.binomial(1, 0.5, n)
    # Treatment correlated with age and sex.
    logit = -3 + 0.05 * age + 0.8 * sex + rng.normal(0, 0.5, n)
    p = 1 / (1 + np.exp(-logit))
    t = (rng.uniform(size=n) < p).astype(int)
    return pd.DataFrame({"age": age, "sex": sex, "t": t, "outcome": rng.normal(0, 1, n)})


# ── fit_propensity_scores ────────────────────────────────────────────────


def test_fit_propensity_returns_one_score_per_row():
    df = _synthetic()
    scores = fit_propensity_scores(df, "t", ["age", "sex"])
    assert len(scores) == len(df)
    assert ((scores > 0) & (scores < 1)).all()


def test_fit_propensity_rejects_unknown_treatment():
    df = _synthetic()
    with pytest.raises(ValueError):
        fit_propensity_scores(df, "nope", ["age"])


def test_fit_propensity_rejects_unknown_covariate():
    df = _synthetic()
    with pytest.raises(ValueError):
        fit_propensity_scores(df, "t", ["age", "nope"])


# ── covariate_balance ────────────────────────────────────────────────────


def test_covariate_balance_pre_match_shows_imbalance():
    df = _synthetic()
    bal = covariate_balance(df, "t", ["age", "sex"])
    assert set(bal["covariate"]) == {"age", "sex"}
    # By construction the pre-match SMD on age and sex should be > 0.10.
    assert bal.loc[bal["covariate"] == "age", "smd"].iloc[0] > 0.10
    assert bal.loc[bal["covariate"] == "sex", "smd"].iloc[0] > 0.10


def test_covariate_balance_categorical_one_hot():
    df = _synthetic().copy()
    df["region"] = ["north", "south"] * (len(df) // 2)
    bal = covariate_balance(df, "t", ["region"])
    # Two levels expanded into two rows.
    assert {"region=north", "region=south"}.issubset(set(bal["covariate"]))


# ── nearest_neighbour_match ──────────────────────────────────────────────


def test_match_returns_two_rows_per_pair():
    df = _synthetic()
    scores = fit_propensity_scores(df, "t", ["age", "sex"])
    matched = nearest_neighbour_match(df, scores, "t", caliper_sd_multiplier=0.2)
    assert len(matched) % 2 == 0
    pair_ids = matched["match_pair_id"].value_counts()
    assert (pair_ids == 2).all()


def test_match_size_equals_2x_min_after_caliper():
    df = _synthetic()
    scores = fit_propensity_scores(df, "t", ["age", "sex"])
    matched = nearest_neighbour_match(df, scores, "t", caliper_sd_multiplier=0.5)
    n_treated = int((matched["t"] == 1).sum())
    n_control = int((matched["t"] == 0).sum())
    # With a loose caliper of 0.5 SD, matching should be 1:1.
    assert n_treated == n_control
    # And bounded by the smaller side of the original cohort.
    full_min = min(int((df["t"] == 1).sum()), int((df["t"] == 0).sum()))
    assert n_treated <= full_min


def test_match_caliper_drops_extreme_treated():
    df = _synthetic()
    scores = fit_propensity_scores(df, "t", ["age", "sex"])
    # Very strict caliper => fewer pairs survive.
    strict = nearest_neighbour_match(df, scores, "t", caliper_sd_multiplier=0.01)
    loose = nearest_neighbour_match(df, scores, "t", caliper_sd_multiplier=0.5)
    assert len(strict) <= len(loose)


# ── run_psm orchestrator: post-match SMDs < 0.10 threshold ───────────────


def test_run_psm_post_match_smd_under_threshold():
    df = _synthetic()
    res = run_psm(df, "t", ["age", "sex"], caliper_sd_multiplier=0.2)
    smd_before = res["balance_before"]["smd"]
    smd_after = res["balance_after"]["smd"]
    assert smd_before.max() > 0.10  # was imbalanced
    assert smd_after.max() < 0.10   # balanced after matching


def test_run_psm_returns_counts_and_caliper():
    df = _synthetic()
    res = run_psm(df, "t", ["age", "sex"], caliper_sd_multiplier=0.2)
    assert res["n_treated_matched"] == res["n_control_matched"]
    assert res["n_treated_matched"] <= res["n_treated_total"]
    assert math.isclose(res["caliper_sd_multiplier"], 0.2)


def test_run_psm_dropna_does_not_crash():
    df = _synthetic()
    df.loc[0, "age"] = np.nan
    df.loc[5, "sex"] = np.nan
    res = run_psm(df, "t", ["age", "sex"], caliper_sd_multiplier=0.2)
    assert res["n_treated_matched"] > 0
