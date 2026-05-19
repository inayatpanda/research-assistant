"""Phase 17 (MP17) — Mixed-effects extensions tests.

Targets:
  * Nested-cluster random effects via ``vc_formula``.
  * Treatment × time interaction expansion.
  * REML vs ML.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from research_api.services.stats.mixed_effects import fit_mixedlm
from research_api.services.stats.runner import run as runner_run


def _make_nested_centre_data(seed: int = 0) -> pd.DataFrame:
    """3 centres × 5 patients × 2 timepoints = 30 rows, ground-truth slope 0.5."""
    rng = np.random.default_rng(seed)
    rows = []
    for centre_idx in range(3):
        centre_offset = rng.normal(0, 1.0)
        for patient_idx in range(5):
            patient_offset = rng.normal(0, 0.5)
            pid = f"c{centre_idx}_p{patient_idx}"
            for t in range(2):
                # outcome: 2.0 + 0.5*t + centre_effect + patient_effect + noise
                y = (
                    2.0
                    + 0.5 * t
                    + centre_offset
                    + patient_offset
                    + rng.normal(0, 0.2)
                )
                rows.append(
                    {
                        "centre": f"c{centre_idx}",
                        "patient_id": pid,
                        "time": float(t),
                        "outcome": float(y),
                    }
                )
    return pd.DataFrame(rows)


# ── Nested-cluster known-answer ─────────────────────────────────────────────


def test_fit_mixedlm_nested_clusters_known_answer():
    df = _make_nested_centre_data()
    summary = fit_mixedlm(
        df,
        outcome="outcome",
        predictors=["time"],
        cluster="centre",
        inner_cluster="patient_id",
    )
    # Slope on `time` should be ~0.5 with this design.
    assert math.isclose(summary["fe_coefs"]["coef_time"], 0.5, abs_tol=0.15)
    assert summary["n_obs"] == 30
    assert summary["n_clusters"] == 3
    assert summary["n_inner_clusters"] == 15  # 3 centres × 5 patients


def test_fit_mixedlm_single_cluster_no_inner():
    df = _make_nested_centre_data()
    summary = fit_mixedlm(
        df,
        outcome="outcome",
        predictors=["time"],
        cluster="patient_id",
    )
    assert summary["n_inner_clusters"] is None


# ── REML / ML toggle ────────────────────────────────────────────────────────


def test_reml_and_ml_give_similar_coefficients_but_distinct_likelihoods():
    df = _make_nested_centre_data(seed=7)
    reml = fit_mixedlm(
        df,
        outcome="outcome",
        predictors=["time"],
        cluster="patient_id",
        reml=True,
    )
    ml = fit_mixedlm(
        df,
        outcome="outcome",
        predictors=["time"],
        cluster="patient_id",
        reml=False,
    )
    # Coefficient very close; likelihoods differ.
    assert math.isclose(
        reml["fe_coefs"]["coef_time"], ml["fe_coefs"]["coef_time"], abs_tol=0.01
    )
    assert reml["reml"] is True
    assert ml["reml"] is False


# ── Interaction expansion ───────────────────────────────────────────────────


def _make_interaction_data(seed: int = 0) -> pd.DataFrame:
    """Time × treatment interaction: treated arm gains 1.0/unit time."""
    rng = np.random.default_rng(seed)
    rows = []
    for pid in range(40):
        treated = pid % 2
        intercept = rng.normal(0, 0.5)
        for t in range(4):
            y = 2.0 + 0.2 * t + 1.0 * t * treated + intercept + rng.normal(0, 0.2)
            rows.append(
                {
                    "patient_id": f"p{pid}",
                    "time": float(t),
                    "treatment": float(treated),
                    "outcome": float(y),
                }
            )
    return pd.DataFrame(rows)


def test_interaction_term_is_significant():
    df = _make_interaction_data()
    out = runner_run(
        test_key="mixed_effects_lm",
        df=df,
        variables={
            "outcome": "outcome",
            "predictors": ["treatment", "time"],
            "cluster": "patient_id",
            "interaction_pair": ["treatment", "time"],
        },
    )
    p_interaction = out.extras["p_treatment:time"]
    assert p_interaction < 0.01
    # Coefficient on interaction term is ~1.0
    coef = out.extras["coef_treatment:time"]
    assert math.isclose(coef, 1.0, abs_tol=0.15)
    assert out.extras["interaction_term"] == "treatment:time"


def test_no_interaction_when_pair_omitted():
    df = _make_interaction_data(seed=11)
    out = runner_run(
        test_key="mixed_effects_lm",
        df=df,
        variables={
            "outcome": "outcome",
            "predictors": ["treatment", "time"],
            "cluster": "patient_id",
        },
    )
    assert out.extras["interaction_term"] is None
    assert "p_treatment:time" not in out.extras


def test_mixed_effects_lm_runner_pass_through_nested():
    df = _make_nested_centre_data()
    out = runner_run(
        test_key="mixed_effects_lm",
        df=df,
        variables={
            "outcome": "outcome",
            "predictors": ["time"],
            "cluster": "centre",
            "inner_cluster": "patient_id",
        },
    )
    assert out.extras["n_clusters"] == 3
    assert out.extras["n_inner_clusters"] == 15
