"""Phase 13 — Propensity-score matching.

Pure functions; no DB / FS / network. Pipeline:

  1. ``fit_propensity_scores(df, treatment_col, covariate_cols)`` returns the
     predicted P(T=1|X) for every row using a sklearn ``LogisticRegression``
     fitted with no penalty (the closest thing to a textbook logistic).
  2. ``nearest_neighbour_match(df, scores, treatment_col, caliper_sd)``
     performs 1:1 greedy nearest-neighbour matching on the *logit* of the
     propensity score with a caliper of ``caliper_sd * SD(logit)``. Rows
     that fail the caliper are dropped.
  3. ``covariate_balance(df, treatment_col, covariate_cols)`` returns a
     DataFrame with one row per covariate giving the absolute standardised
     mean difference (SMD). Used pre and post matching.

Standardised mean difference (continuous covariate)::

    smd = |mean_treated - mean_control| / sqrt((var_treated + var_control) / 2)

Common threshold: |SMD| < 0.10 indicates good balance.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _coerce_treatment_binary(series: pd.Series) -> pd.Series:
    """Map a 2-valued series to {0, 1}. The larger / 'true-y' value becomes 1."""
    levels = series.dropna().unique().tolist()
    if len(levels) != 2:
        raise ValueError(
            f"treatment must have exactly 2 levels, got {len(levels)} ({levels!r})"
        )
    # Prefer numeric ordering when both levels are numeric/boolean.
    try:
        as_num = sorted(levels, key=lambda v: float(v))
        zero_val, one_val = as_num[0], as_num[1]
    except (TypeError, ValueError):
        as_str = sorted(levels, key=str)
        zero_val, one_val = as_str[0], as_str[1]
    return series.map({zero_val: 0, one_val: 1}).astype("Int64")


def _covariate_matrix(df: pd.DataFrame, covariate_cols: list[str]) -> np.ndarray:
    """Convert covariate columns to a float matrix, one-hot-encoding strings."""
    pieces: list[np.ndarray] = []
    for col in covariate_cols:
        s = df[col]
        if pd.api.types.is_numeric_dtype(s):
            pieces.append(s.to_numpy(dtype=float).reshape(-1, 1))
        else:
            dummies = pd.get_dummies(s.astype(str), drop_first=True, dummy_na=False)
            pieces.append(dummies.to_numpy(dtype=float))
    if not pieces:
        return np.zeros((len(df), 0), dtype=float)
    return np.hstack(pieces)


def fit_propensity_scores(
    df: pd.DataFrame,
    treatment_col: str,
    covariate_cols: list[str],
) -> pd.Series:
    """Fit a logistic regression of treatment ~ covariates and return P(T=1)."""
    from sklearn.linear_model import LogisticRegression

    if treatment_col not in df.columns:
        raise ValueError(f"treatment_col {treatment_col!r} not found")
    missing = [c for c in covariate_cols if c not in df.columns]
    if missing:
        raise ValueError(f"covariate_cols not found: {missing!r}")

    sub = df[[treatment_col, *covariate_cols]].dropna().reset_index(drop=True)
    if sub.empty:
        raise ValueError("no rows remain after dropping NaN on treatment + covariates")

    y = _coerce_treatment_binary(sub[treatment_col]).to_numpy(dtype=int)
    X = _covariate_matrix(sub, covariate_cols)

    if X.shape[1] == 0:
        raise ValueError("at least one covariate is required")

    model = LogisticRegression(
        solver="lbfgs",
        C=1e6,           # near-zero regularisation ~ textbook logistic
        max_iter=500,
    )
    model.fit(X, y)
    probs = model.predict_proba(X)[:, 1]
    scores = pd.Series(np.nan, index=df.index, dtype=float)
    # Map back from the dropped-NaN subset to the original frame index.
    sub_index_in_orig = df[[treatment_col, *covariate_cols]].dropna().index
    scores.loc[sub_index_in_orig] = probs
    return scores


def _logit(p: float) -> float:
    eps = 1e-9
    p = min(max(p, eps), 1.0 - eps)
    return math.log(p / (1.0 - p))


def nearest_neighbour_match(
    df: pd.DataFrame,
    propensity_scores: pd.Series,
    treatment_col: str,
    caliper_sd_multiplier: float = 0.2,
) -> pd.DataFrame:
    """1:1 greedy nearest-neighbour matching on logit(propensity).

    Rows whose nearest available control exceeds the caliper distance are
    dropped (along with the would-be control). Output is the matched
    subset of ``df`` with an added ``match_pair_id`` column.
    """
    if treatment_col not in df.columns:
        raise ValueError(f"treatment_col {treatment_col!r} not found")
    if propensity_scores.index.equals(df.index) is False:
        # accept any alignment by reindexing
        propensity_scores = propensity_scores.reindex(df.index)

    treatment_bin = _coerce_treatment_binary(df[treatment_col])
    work = df.copy()
    work["__t__"] = treatment_bin
    work["__ps__"] = propensity_scores
    work = work.dropna(subset=["__t__", "__ps__"]).reset_index(drop=True)

    treated = work[work["__t__"] == 1].copy()
    control = work[work["__t__"] == 0].copy()
    if treated.empty or control.empty:
        return work.drop(columns=["__t__", "__ps__"]).iloc[0:0].copy()

    logits = work["__ps__"].apply(_logit)
    sd_logit = float(np.std(logits.to_numpy(), ddof=1))
    if not math.isfinite(sd_logit) or sd_logit == 0:
        sd_logit = 1.0
    caliper = caliper_sd_multiplier * sd_logit

    treated["__logit__"] = treated["__ps__"].apply(_logit)
    control["__logit__"] = control["__ps__"].apply(_logit)

    used_control_idx: set[int] = set()
    pairs: list[tuple[int, int]] = []
    # Greedy: iterate treated in order of decreasing |logit|, which improves
    # match quality on the extremes per Austin 2011.
    treated_sorted = treated.assign(__abs_logit__=treated["__logit__"].abs()).sort_values(
        "__abs_logit__", ascending=False
    )

    for t_idx, t_row in treated_sorted.iterrows():
        t_logit = t_row["__logit__"]
        # Find nearest available control.
        best_c_idx: int | None = None
        best_dist = float("inf")
        for c_idx, c_row in control.iterrows():
            if c_idx in used_control_idx:
                continue
            d = abs(c_row["__logit__"] - t_logit)
            if d < best_dist:
                best_dist = d
                best_c_idx = c_idx
        if best_c_idx is None:
            continue
        if best_dist > caliper:
            continue
        used_control_idx.add(best_c_idx)
        pairs.append((t_idx, best_c_idx))

    if not pairs:
        return work.drop(columns=["__t__", "__ps__"]).iloc[0:0].copy()

    rows: list[pd.Series] = []
    for pair_id, (t_idx, c_idx) in enumerate(pairs):
        t_r = work.loc[t_idx].copy()
        c_r = work.loc[c_idx].copy()
        t_r["match_pair_id"] = pair_id
        c_r["match_pair_id"] = pair_id
        rows.append(t_r)
        rows.append(c_r)
    out = pd.DataFrame(rows).reset_index(drop=True)
    return out.drop(columns=["__t__", "__ps__"], errors="ignore")


def covariate_balance(
    df: pd.DataFrame,
    treatment_col: str,
    covariate_cols: list[str],
) -> pd.DataFrame:
    """Per-covariate absolute SMD between treated and control.

    Categorical covariates are one-hot encoded (each level becomes a row in
    the output table).
    """
    if treatment_col not in df.columns:
        raise ValueError(f"treatment_col {treatment_col!r} not found")
    missing = [c for c in covariate_cols if c not in df.columns]
    if missing:
        raise ValueError(f"covariate_cols not found: {missing!r}")

    sub = df[[treatment_col, *covariate_cols]].dropna().copy()
    if sub.empty:
        return pd.DataFrame(columns=["covariate", "smd", "mean_treated", "mean_control"])

    t = _coerce_treatment_binary(sub[treatment_col])
    rows: list[dict[str, float | str]] = []
    for col in covariate_cols:
        s = sub[col]
        if pd.api.types.is_numeric_dtype(s):
            rows.append(_smd_row(col, s.astype(float), t))
        else:
            dummies = pd.get_dummies(s.astype(str), drop_first=False, dummy_na=False)
            for level in dummies.columns:
                rows.append(_smd_row(f"{col}={level}", dummies[level].astype(float), t))
    return pd.DataFrame(rows)


def _smd_row(label: str, values: pd.Series, treatment: pd.Series) -> dict[str, float | str]:
    treated = values[treatment == 1].to_numpy(dtype=float)
    control = values[treatment == 0].to_numpy(dtype=float)
    if len(treated) == 0 or len(control) == 0:
        return {
            "covariate": label,
            "smd": float("nan"),
            "mean_treated": float("nan"),
            "mean_control": float("nan"),
        }
    mean_t = float(treated.mean())
    mean_c = float(control.mean())
    var_t = float(treated.var(ddof=1)) if len(treated) > 1 else 0.0
    var_c = float(control.var(ddof=1)) if len(control) > 1 else 0.0
    pooled = math.sqrt((var_t + var_c) / 2.0) if (var_t + var_c) > 0 else 0.0
    smd = abs(mean_t - mean_c) / pooled if pooled > 0 else 0.0
    return {
        "covariate": label,
        "smd": float(smd),
        "mean_treated": mean_t,
        "mean_control": mean_c,
    }


def run_psm(
    df: pd.DataFrame,
    treatment_col: str,
    covariate_cols: list[str],
    caliper_sd_multiplier: float = 0.2,
) -> dict[str, object]:
    """Convenience orchestrator: fit + match + balance pre/post.

    Returns dict suitable for the route layer:
      {
        "matched_df": pd.DataFrame,
        "balance_before": pd.DataFrame,
        "balance_after": pd.DataFrame,
        "n_treated_total": int,
        "n_control_total": int,
        "n_treated_matched": int,
        "n_control_matched": int,
        "caliper_sd_multiplier": float,
      }
    """
    scores = fit_propensity_scores(df, treatment_col, covariate_cols)
    matched = nearest_neighbour_match(
        df, scores, treatment_col, caliper_sd_multiplier=caliper_sd_multiplier
    )
    before = covariate_balance(df, treatment_col, covariate_cols)
    after = (
        covariate_balance(matched, treatment_col, covariate_cols)
        if not matched.empty
        else before.assign(smd=float("nan"))
    )

    t_full = _coerce_treatment_binary(df[treatment_col].dropna())
    t_matched = (
        _coerce_treatment_binary(matched[treatment_col].dropna()) if not matched.empty else pd.Series(dtype="Int64")
    )

    return {
        "matched_df": matched,
        "balance_before": before,
        "balance_after": after,
        "n_treated_total": int((t_full == 1).sum()),
        "n_control_total": int((t_full == 0).sum()),
        "n_treated_matched": int((t_matched == 1).sum()),
        "n_control_matched": int((t_matched == 0).sum()),
        "caliper_sd_multiplier": float(caliper_sd_multiplier),
    }


__all__ = [
    "fit_propensity_scores",
    "nearest_neighbour_match",
    "covariate_balance",
    "run_psm",
]
