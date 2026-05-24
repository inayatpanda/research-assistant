"""F3 Pathway 1 — Two-group comparison.

Inputs:
  * outcome column (numeric OR categorical with >=2 levels)
  * group column (categorical with exactly 2 levels)

Auto test-selection (numeric outcome):
  1. Shapiro-Wilk normality on each group.
  2. If both p > 0.05, distribution is normal:
     - Levene's test for equality of variances.
     - p_levene < 0.05 → Welch's t-test, else Student's t-test.
  3. Otherwise (any group non-normal) → Mann-Whitney U.

Categorical outcome:
  * 2x2 table: if any expected cell < 5 → Fisher's exact, else chi-square.
  * >2 levels → chi-square (with sparse-category warning).
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


def _is_numeric(series: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return True
    # Try coercion — some uploaded columns come in as object but are numeric.
    coerced = pd.to_numeric(series, errors="coerce")
    return coerced.notna().sum() / max(len(series), 1) > 0.8


def _shapiro(arr: np.ndarray) -> float:
    if len(arr) < 3:
        return float("nan")
    if len(arr) > 5000:
        arr = np.random.default_rng(0).choice(arr, size=5000, replace=False)
    try:
        return float(stats.shapiro(arr).pvalue)
    except Exception:
        return float("nan")


def _cohen_d(a: np.ndarray, b: np.ndarray) -> float:
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return float("nan")
    s1 = a.var(ddof=1)
    s2 = b.var(ddof=1)
    pooled = np.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
    if pooled <= 0:
        return float("nan")
    return float((a.mean() - b.mean()) / pooled)


def _describe_numeric(arr: np.ndarray) -> dict[str, float]:
    if len(arr) == 0:
        return {"n": 0, "mean": float("nan"), "sd": float("nan"),
                "median": float("nan"), "q1": float("nan"), "q3": float("nan")}
    return {
        "n": int(len(arr)),
        "mean": float(np.mean(arr)),
        "sd": float(np.std(arr, ddof=1)) if len(arr) > 1 else float("nan"),
        "median": float(np.median(arr)),
        "q1": float(np.quantile(arr, 0.25)),
        "q3": float(np.quantile(arr, 0.75)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def _odds_ratio_ci(table: np.ndarray) -> tuple[float, float, float]:
    """Haldane-corrected OR + Woolf 95% CI for a 2x2 table.

    Returns (or, ci_low, ci_high). NaN when impossible to compute.
    """
    a, b = float(table[0, 0]), float(table[0, 1])
    c, d = float(table[1, 0]), float(table[1, 1])
    # Add 0.5 to every cell when any cell is 0 (Haldane).
    if min(a, b, c, d) == 0:
        a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
    or_val = (a * d) / (b * c) if (b * c) > 0 else float("nan")
    if not np.isfinite(or_val) or or_val <= 0:
        return or_val, float("nan"), float("nan")
    se = float(np.sqrt(1 / a + 1 / b + 1 / c + 1 / d))
    ln_or = float(np.log(or_val))
    return or_val, float(np.exp(ln_or - 1.96 * se)), float(np.exp(ln_or + 1.96 * se))


def run(
    df: pd.DataFrame,
    *,
    outcome: str,
    group: str,
) -> dict[str, Any]:
    """Execute the two-group pathway and return a result blob.

    Raises ValueError on invalid inputs (missing columns, wrong group
    count, all-same values, etc.). The route layer turns these into
    HTTP 422.
    """
    if outcome not in df.columns:
        raise ValueError(f"outcome column '{outcome}' not in dataset")
    if group not in df.columns:
        raise ValueError(f"group column '{group}' not in dataset")
    if outcome == group:
        raise ValueError("outcome and group columns must differ")

    clean = df[[outcome, group]].dropna()
    if clean.empty:
        raise ValueError("no rows with non-missing values for both columns")

    levels = clean[group].astype(str).unique().tolist()
    levels.sort()
    if len(levels) != 2:
        raise ValueError(
            f"group column '{group}' must have exactly 2 levels, found {len(levels)}"
        )
    level_a, level_b = levels

    a_rows = clean.loc[clean[group].astype(str) == level_a, outcome]
    b_rows = clean.loc[clean[group].astype(str) == level_b, outcome]

    if len(a_rows) < 2 or len(b_rows) < 2:
        raise ValueError("each group must have at least 2 non-missing observations")

    is_numeric = _is_numeric(clean[outcome])

    if is_numeric:
        a = pd.to_numeric(a_rows, errors="coerce").dropna().to_numpy(dtype=float)
        b = pd.to_numeric(b_rows, errors="coerce").dropna().to_numpy(dtype=float)
        # Guard: all-same values give zero variance.
        if float(np.var(a)) == 0 and float(np.var(b)) == 0:
            raise ValueError("outcome has zero variance in both groups; cannot compare")

        # Step 1 — normality.
        p_norm_a = _shapiro(a)
        p_norm_b = _shapiro(b)
        normal = (
            np.isfinite(p_norm_a) and p_norm_a > 0.05
            and np.isfinite(p_norm_b) and p_norm_b > 0.05
        )

        # Step 2 — Levene (only meaningful when normal).
        try:
            p_levene = float(stats.levene(a, b, center="median").pvalue)
        except Exception:
            p_levene = float("nan")

        if normal:
            equal_var = not (np.isfinite(p_levene) and p_levene < 0.05)
            t, p = stats.ttest_ind(a, b, equal_var=equal_var)
            test_used = "student_t" if equal_var else "welch_t"
            n1, n2 = len(a), len(b)
            # CI on mean difference (Welch uses Satterthwaite df).
            mean_diff = float(a.mean() - b.mean())
            if equal_var:
                pooled = np.sqrt(
                    ((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1))
                    / (n1 + n2 - 2)
                )
                se = float(pooled * np.sqrt(1.0 / n1 + 1.0 / n2))
                df_val = float(n1 + n2 - 2)
            else:
                v1 = a.var(ddof=1) / n1
                v2 = b.var(ddof=1) / n2
                se = float(np.sqrt(v1 + v2))
                df_val = float(((v1 + v2) ** 2) / (v1**2 / (n1 - 1) + v2**2 / (n2 - 1)))
            crit = float(stats.t.ppf(0.975, df_val))
            ci_low = mean_diff - crit * se
            ci_high = mean_diff + crit * se
            effect = _cohen_d(a, b)
            effect_label = "cohens_d"
        else:
            u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
            test_used = "mann_whitney"
            n1, n2 = len(a), len(b)
            t = float(u)
            df_val = None
            # Rank-biserial effect size.
            effect = float(1.0 - (2.0 * u) / (n1 * n2))
            effect_label = "rank_biserial"
            mean_diff = float(np.median(a) - np.median(b))
            ci_low = float("nan")
            ci_high = float("nan")

        return {
            "pathway": "two_group",
            "outcome_type": "numeric",
            "outcome": outcome,
            "group": group,
            "level_a": level_a,
            "level_b": level_b,
            "n_a": int(len(a)),
            "n_b": int(len(b)),
            "descriptives": {
                level_a: _describe_numeric(a),
                level_b: _describe_numeric(b),
            },
            "assumptions": {
                "shapiro_p_a": p_norm_a,
                "shapiro_p_b": p_norm_b,
                "levene_p": p_levene,
                "normal": bool(normal),
            },
            "test_used": test_used,
            "statistic": float(t),
            "p_value": float(p),
            "df": df_val,
            "mean_diff": float(mean_diff),
            "ci_low": float(ci_low) if np.isfinite(ci_low) else None,
            "ci_high": float(ci_high) if np.isfinite(ci_high) else None,
            "effect_size": float(effect) if np.isfinite(effect) else None,
            "effect_label": effect_label,
        }

    # Categorical outcome path.
    outcome_levels = sorted(clean[outcome].astype(str).unique().tolist())
    if len(outcome_levels) < 2:
        raise ValueError("categorical outcome must have >= 2 levels")

    table = pd.crosstab(clean[outcome].astype(str), clean[group].astype(str))
    table = table.reindex(index=outcome_levels, columns=[level_a, level_b], fill_value=0)
    obs = table.values.astype(float)
    chi2, p, dof, expected = stats.chi2_contingency(obs, correction=False)
    expected_min = float(expected.min())

    is_2x2 = obs.shape == (2, 2)
    use_fisher = is_2x2 and expected_min < 5.0
    sparse_warning = (not is_2x2) and expected_min < 5.0

    result: dict[str, Any] = {
        "pathway": "two_group",
        "outcome_type": "categorical",
        "outcome": outcome,
        "group": group,
        "level_a": level_a,
        "level_b": level_b,
        "n_a": int(obs[:, 1].sum()) if False else int(obs.sum(axis=0)[0]),
        "n_b": int(obs.sum(axis=0)[1]),
        "outcome_levels": outcome_levels,
        "table": obs.astype(int).tolist(),
        "expected_min": expected_min,
        "sparse_warning": bool(sparse_warning),
    }

    if use_fisher:
        odds, p_fisher = stats.fisher_exact(obs)
        or_val, ci_low, ci_high = _odds_ratio_ci(obs)
        result.update(
            {
                "test_used": "fisher_exact",
                "statistic": float(odds),
                "p_value": float(p_fisher),
                "df": None,
                "odds_ratio": float(or_val) if np.isfinite(or_val) else None,
                "ci_low": float(ci_low) if np.isfinite(ci_low) else None,
                "ci_high": float(ci_high) if np.isfinite(ci_high) else None,
                "effect_size": float(or_val) if np.isfinite(or_val) else None,
                "effect_label": "odds_ratio",
            }
        )
    else:
        n = int(obs.sum())
        min_dim = min(obs.shape[0] - 1, obs.shape[1] - 1)
        cramers_v = float(np.sqrt(chi2 / (n * min_dim))) if min_dim > 0 else float("nan")
        result.update(
            {
                "test_used": "chi_squared",
                "statistic": float(chi2),
                "p_value": float(p),
                "df": float(dof),
                "effect_size": cramers_v if np.isfinite(cramers_v) else None,
                "effect_label": "cramers_v",
            }
        )
        if is_2x2:
            or_val, ci_low, ci_high = _odds_ratio_ci(obs)
            result["odds_ratio"] = float(or_val) if np.isfinite(or_val) else None
            result["ci_low"] = float(ci_low) if np.isfinite(ci_low) else None
            result["ci_high"] = float(ci_high) if np.isfinite(ci_high) else None
    return result
