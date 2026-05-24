"""F3 Pathway 2 — Risk factor identification.

Univariable AND multivariable regression side-by-side for the same set
of predictors. Outcome decides whether we run logistic (binary) or
linear (continuous). Optional confounders are forced into the model.

Outputs (per predictor):
  * Univariable estimate (OR/beta) + 95% CI + p
  * Multivariable estimate (OR/beta) + 95% CI + p
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf


def _is_numeric(series: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return True
    coerced = pd.to_numeric(series, errors="coerce")
    return coerced.notna().sum() / max(len(series), 1) > 0.8


def _is_binary(series: pd.Series) -> bool:
    vals = pd.to_numeric(series, errors="coerce").dropna().unique().tolist()
    return set(vals).issubset({0, 1, 0.0, 1.0}) and len(vals) == 2


def _formula(outcome: str, predictors: list[str], df: pd.DataFrame) -> str:
    parts: list[str] = []
    for p in predictors:
        col = df[p]
        if pd.api.types.is_numeric_dtype(col):
            parts.append(p)
        else:
            parts.append(f"C({p})")
    return f"{outcome} ~ " + " + ".join(parts) if parts else f"{outcome} ~ 1"


def _coef_rows(model, term: str, is_logistic: bool) -> list[dict[str, Any]]:
    """Return one dict per coefficient that involves the original term.

    For a categorical predictor ``C(arm)``, statsmodels emits levels like
    ``C(arm)[T.B]``. We surface each of those rows separately.
    """
    out: list[dict[str, Any]] = []
    params = model.params
    conf = model.conf_int(alpha=0.05)
    pvals = model.pvalues
    matches = [name for name in params.index if term in name and name != "Intercept"]
    if not matches:
        return out
    for name in matches:
        coef = float(params[name])
        ci_lo, ci_hi = float(conf.loc[name][0]), float(conf.loc[name][1])
        pv = float(pvals[name])
        if is_logistic:
            out.append(
                {
                    "term": name,
                    "estimate": float(np.exp(coef)),
                    "estimate_label": "OR",
                    "ci_low": float(np.exp(ci_lo)),
                    "ci_high": float(np.exp(ci_hi)),
                    "p_value": pv,
                    "log_estimate": coef,
                }
            )
        else:
            out.append(
                {
                    "term": name,
                    "estimate": coef,
                    "estimate_label": "beta",
                    "ci_low": ci_lo,
                    "ci_high": ci_hi,
                    "p_value": pv,
                }
            )
    return out


def _hosmer_lemeshow(y: np.ndarray, p: np.ndarray, g: int = 10) -> dict[str, float]:
    """Hosmer-Lemeshow goodness-of-fit test (binary logistic).

    Returns {"chi2", "p_value", "df"}. ``g`` is the number of probability
    deciles. Falls back gracefully when there aren't enough unique values.
    """
    if len(y) < g * 2:
        return {"chi2": float("nan"), "p_value": float("nan"), "df": float("nan")}
    order = np.argsort(p)
    p_sorted = p[order]
    y_sorted = y[order]
    quantile_edges = np.quantile(p_sorted, np.linspace(0, 1, g + 1))
    # Make edges strictly increasing for digitize.
    quantile_edges = np.unique(quantile_edges)
    if len(quantile_edges) - 1 < 2:
        return {"chi2": float("nan"), "p_value": float("nan"), "df": float("nan")}
    bins = np.digitize(p_sorted, quantile_edges[1:-1])
    chi2 = 0.0
    valid_groups = 0
    for b in np.unique(bins):
        mask = bins == b
        obs_pos = float(y_sorted[mask].sum())
        exp_pos = float(p_sorted[mask].sum())
        n_b = float(mask.sum())
        if n_b == 0 or exp_pos <= 0 or exp_pos >= n_b:
            continue
        obs_neg = n_b - obs_pos
        exp_neg = n_b - exp_pos
        chi2 += (obs_pos - exp_pos) ** 2 / exp_pos
        chi2 += (obs_neg - exp_neg) ** 2 / exp_neg
        valid_groups += 1
    df = max(valid_groups - 2, 1)
    from scipy import stats as _s
    p_value = float(1.0 - _s.chi2.cdf(chi2, df))
    return {"chi2": float(chi2), "p_value": p_value, "df": float(df)}


def _auc(y: np.ndarray, p: np.ndarray) -> float:
    """Trapezoidal ROC AUC. Returns NaN on degenerate input."""
    if len(y) == 0:
        return float("nan")
    order = np.argsort(-p)
    y_sorted = y[order]
    pos = float(y_sorted.sum())
    neg = float(len(y) - pos)
    if pos == 0 or neg == 0:
        return float("nan")
    tps = np.cumsum(y_sorted)
    fps = np.cumsum(1 - y_sorted)
    tpr = np.concatenate(([0.0], tps / pos))
    fpr = np.concatenate(([0.0], fps / neg))
    trap = getattr(np, "trapezoid", None) or np.trapz  # numpy 2.x rename
    auc = float(trap(tpr, fpr))
    return auc


def _vif_max(df: pd.DataFrame, predictors: list[str]) -> float:
    """Compute the maximum VIF across numeric predictors only.

    Returns NaN if fewer than 2 numeric predictors are available.
    """
    num_preds = [p for p in predictors if pd.api.types.is_numeric_dtype(df[p])]
    if len(num_preds) < 2:
        return float("nan")
    X = df[num_preds].dropna().to_numpy(dtype=float)
    if X.shape[0] < len(num_preds) + 1:
        return float("nan")
    # VIF_i = 1 / (1 - R_i^2) where R_i is OLS of x_i on the others.
    max_vif = 0.0
    n, k = X.shape
    for i in range(k):
        y = X[:, i]
        others = np.delete(X, i, axis=1)
        if others.shape[1] == 0:
            continue
        X1 = np.column_stack([np.ones(n), others])
        try:
            beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
            pred = X1 @ beta
            ss_res = float(np.sum((y - pred) ** 2))
            ss_tot = float(np.sum((y - y.mean()) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            vif = 1.0 / max(1.0 - r2, 1e-10)
            max_vif = max(max_vif, vif)
        except Exception:
            continue
    return float(max_vif) if max_vif > 0 else float("nan")


def run(
    df: pd.DataFrame,
    *,
    outcome: str,
    predictors: list[str],
    confounders: list[str] | None = None,
) -> dict[str, Any]:
    if outcome not in df.columns:
        raise ValueError(f"outcome column '{outcome}' not in dataset")
    if not predictors:
        raise ValueError("predictors list is empty")
    for p in predictors:
        if p not in df.columns:
            raise ValueError(f"predictor '{p}' not in dataset")
        if p == outcome:
            raise ValueError(f"predictor '{p}' duplicates the outcome column")
    confounders = list(confounders or [])
    for c in confounders:
        if c not in df.columns:
            raise ValueError(f"confounder '{c}' not in dataset")
        if c == outcome:
            raise ValueError("confounder cannot equal the outcome column")

    use_cols = [outcome] + predictors + confounders
    clean = df[use_cols].dropna().copy()
    if len(clean) < len(predictors) + len(confounders) + 2:
        raise ValueError("not enough complete-case rows to fit the model")

    is_logistic = _is_binary(clean[outcome])
    if is_logistic:
        clean[outcome] = pd.to_numeric(clean[outcome], errors="coerce")
    else:
        if not _is_numeric(clean[outcome]):
            raise ValueError(
                f"outcome '{outcome}' is neither binary nor numeric"
            )
        clean[outcome] = pd.to_numeric(clean[outcome], errors="coerce")
    clean = clean.dropna(subset=[outcome])

    # Univariable: one model per predictor, ignore confounders.
    univariable: list[dict[str, Any]] = []
    for pred in predictors:
        try:
            formula = _formula(outcome, [pred], clean)
            if is_logistic:
                model = smf.logit(formula, data=clean).fit(disp=0)
            else:
                model = smf.ols(formula, data=clean).fit()
            univariable.extend(_coef_rows(model, pred, is_logistic))
        except Exception as exc:  # noqa: BLE001
            univariable.append(
                {
                    "term": pred,
                    "estimate": None,
                    "estimate_label": "OR" if is_logistic else "beta",
                    "ci_low": None,
                    "ci_high": None,
                    "p_value": None,
                    "error": str(exc),
                }
            )

    # Multivariable: all predictors + confounders together.
    multivariable: list[dict[str, Any]] = []
    omnibus: dict[str, Any] = {}
    try:
        all_terms = predictors + confounders
        formula = _formula(outcome, all_terms, clean)
        if is_logistic:
            mv_model = smf.logit(formula, data=clean).fit(disp=0)
        else:
            mv_model = smf.ols(formula, data=clean).fit()
        for term in all_terms:
            multivariable.extend(_coef_rows(mv_model, term, is_logistic))
        if is_logistic:
            y_arr = clean[outcome].to_numpy(dtype=float)
            p_arr = mv_model.predict(clean).to_numpy(dtype=float)
            hl = _hosmer_lemeshow(y_arr, p_arr)
            omnibus = {
                "pseudo_r2": float(mv_model.prsquared),
                "log_likelihood": float(mv_model.llf),
                "llr_p": float(mv_model.llr_pvalue),
                "hosmer_lemeshow_chi2": hl["chi2"],
                "hosmer_lemeshow_p": hl["p_value"],
                "hosmer_lemeshow_df": hl["df"],
                "auc": _auc(y_arr, p_arr),
            }
        else:
            omnibus = {
                "r_squared": float(mv_model.rsquared),
                "adj_r_squared": float(mv_model.rsquared_adj),
                "f_statistic": float(mv_model.fvalue),
                "f_p_value": float(mv_model.f_pvalue),
            }
        vif_max = _vif_max(clean, all_terms)
        omnibus["max_vif"] = vif_max
        omnibus["multicollinearity_warning"] = bool(np.isfinite(vif_max) and vif_max > 5.0)
        n_used = int(mv_model.nobs)
    except Exception as exc:  # noqa: BLE001
        omnibus = {"error": str(exc)}
        n_used = len(clean)

    return {
        "pathway": "risk_factors",
        "outcome": outcome,
        "outcome_type": "binary" if is_logistic else "continuous",
        "predictors": predictors,
        "confounders": confounders,
        "model": "logistic" if is_logistic else "linear",
        "n": n_used,
        "univariable": univariable,
        "multivariable": multivariable,
        "omnibus": omnibus,
    }
