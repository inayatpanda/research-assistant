"""Phase 17 (MP17) — Linear mixed-effects helpers (split from runner.py).

Single function ``fit_mixedlm`` covering:

  * Single-cluster random intercept (existing behaviour from MP13).
  * Nested-cluster random effects (e.g. ``patient`` nested in ``centre``)
    via statsmodels' ``vc_formula`` syntax.
  * REML vs ML.
  * Treatment × time interaction expansion (toggle).

The function is pure: it accepts a DataFrame + a config dict and returns a
plain summary dict. ``runner._mixed_effects_lm`` delegates to it.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def fit_mixedlm(
    df: pd.DataFrame,
    *,
    outcome: str,
    predictors: list[str],
    cluster: str,
    inner_cluster: str | None = None,
    reml: bool = True,
    interaction_pair: tuple[str, str] | None = None,
    cov_struct: str = "unstructured",
) -> dict[str, Any]:
    """Fit a linear mixed-effects model.

    Parameters
    ----------
    df:
        The fitted-on data (no NaNs in the model columns; the caller drops).
    outcome, predictors, cluster:
        Standard MixedLM inputs.
    inner_cluster:
        Optional second-level group (nested under ``cluster``). When set, a
        statsmodels ``vc_formula`` is used so that the inner cluster is a
        variance component within each outer ``cluster``.
    reml:
        Restricted ML (default) vs ML.
    interaction_pair:
        Optional ``(a, b)`` — appends ``a:b`` to the formula. Statsmodels'
        ``smf.mixedlm`` does NOT support the lme4 ``treatment * time``
        shorthand directly, so we expand to ``a + b + a:b`` for clarity.
    cov_struct:
        Cosmetic only at v1 — statsmodels' MixedLM uses an unstructured
        covariance for the random effects by default. Recorded in the result
        for the report layer.
    """
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    if not predictors:
        raise ValueError("predictors must be a non-empty list")
    rhs = list(predictors)
    if interaction_pair is not None:
        a, b = interaction_pair
        if a not in rhs:
            rhs.append(a)
        if b not in rhs:
            rhs.append(b)
        rhs.append(f"{a}:{b}")
    formula = f"{outcome} ~ " + " + ".join(rhs)

    kwargs: dict[str, Any] = {"groups": df[cluster]}
    if inner_cluster is not None:
        # statsmodels vc_formula syntax: "0 + C(inner_col)" creates a random
        # effect for each level of `inner` within each outer group.
        kwargs["vc_formula"] = {"inner": f"0 + C({inner_cluster})"}
    model = smf.mixedlm(formula, data=df, **kwargs)
    # Bug discovered during MP17 dev: when the random-effects covariance
    # becomes near-singular (small per-cluster variance), the L-BFGS gradient
    # step in statsmodels raises ``numpy.linalg.LinAlgError`` inside
    # ``score_full``. The supported workaround is to fall back to a list of
    # methods; statsmodels tries each in order until one converges.
    try:
        fit = model.fit(reml=reml, method=["lbfgs", "bfgs", "powell"])
    except np.linalg.LinAlgError:
        fit = model.fit(reml=reml, method="powell")

    fe_coefs = {f"coef_{name}": float(fit.fe_params.get(name, float("nan"))) for name in rhs}
    fe_pvals = {f"p_{name}": float(fit.pvalues.get(name, float("nan"))) for name in rhs}
    fe_se = {f"se_{name}": float(fit.bse.get(name, float("nan"))) for name in rhs}

    re_var: float | None
    try:
        cov_re = fit.cov_re
        if hasattr(cov_re, "iloc"):
            re_var = float(cov_re.iloc[0, 0])
        else:
            re_var = float(np.asarray(cov_re).flat[0])
    except Exception:  # noqa: BLE001 — keep best-effort
        log.debug("could not read cov_re", exc_info=True)
        re_var = None

    return {
        "formula": formula,
        "reml": bool(reml),
        "cov_structure": cov_struct,
        "n_obs": int(fit.nobs),
        "n_clusters": int(df[cluster].nunique()),
        "n_inner_clusters": (
            int(df[inner_cluster].nunique()) if inner_cluster else None
        ),
        "log_likelihood": float(fit.llf) if fit.llf is not None else None,
        "aic": float(fit.aic) if hasattr(fit, "aic") and fit.aic is not None else None,
        "bic": float(fit.bic) if hasattr(fit, "bic") and fit.bic is not None else None,
        "random_intercept_var": re_var,
        "fe_coefs": fe_coefs,
        "fe_pvals": fe_pvals,
        "fe_se": fe_se,
        "intercept": float(fit.fe_params.get("Intercept", float("nan"))),
        "interaction_term": (
            f"{interaction_pair[0]}:{interaction_pair[1]}"
            if interaction_pair
            else None
        ),
        "predictor_names": rhs,
    }


__all__ = ["fit_mixedlm"]
