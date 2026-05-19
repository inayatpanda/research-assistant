"""Phase 17 (MP17) — Missing-data sensitivity analyses.

Three procedures:

  * ``worst_case``: assigns the worst possible outcome value (max of "bad"
    direction) to every missing row, then runs a Welch t-test between two
    groups.
  * ``best_case``: mirror of worst-case using the best possible value.
  * ``tipping_point``: bisects over candidate imputation values for the
    missing rows in the *treatment* arm until significance flips, returning
    the threshold imputation value at which p crosses ``alpha``.

All three accept a DataFrame, an outcome column, a 2-level group column,
and return a flat result dict.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


def _two_group_arrays(
    df: pd.DataFrame, outcome: str, group: str
) -> tuple[np.ndarray, np.ndarray]:
    levels = sorted(df[group].dropna().unique().tolist(), key=str)
    if len(levels) != 2:
        raise ValueError(
            f"expected exactly 2 groups in {group!r}, found {len(levels)}"
        )
    a = df.loc[df[group] == levels[0], outcome].to_numpy(dtype=float)
    b = df.loc[df[group] == levels[1], outcome].to_numpy(dtype=float)
    return a, b


def _welch(a: np.ndarray, b: np.ndarray) -> tuple[float, float, float]:
    """Welch t-test → (mean_diff, t_stat, p)."""
    a_obs = a[~np.isnan(a)]
    b_obs = b[~np.isnan(b)]
    t_stat, p = stats.ttest_ind(a_obs, b_obs, equal_var=False)
    mean_diff = float(np.mean(a_obs) - np.mean(b_obs))
    return mean_diff, float(t_stat), float(p)


def worst_case(
    df: pd.DataFrame,
    *,
    outcome: str,
    group: str,
    direction: str = "higher_better",
) -> dict[str, Any]:
    """Worst-case sensitivity: every missing outcome gets the WORST possible
    value (so as to maximally penalise the favoured arm).

    For ``higher_better``, missing rows in the favoured arm are set to the
    observed minimum across both arms; missing rows in the comparator arm
    are set to the observed maximum. For ``lower_better`` we mirror.
    """
    if direction not in ("higher_better", "lower_better"):
        raise ValueError("direction must be 'higher_better' or 'lower_better'")
    a, b = _two_group_arrays(df, outcome, group)
    all_obs = np.concatenate([a[~np.isnan(a)], b[~np.isnan(b)]])
    if all_obs.size == 0:
        raise ValueError("no observed values to derive worst-case bounds")
    obs_min, obs_max = float(np.min(all_obs)), float(np.max(all_obs))
    if direction == "higher_better":
        # arm A "favoured" → fill its missing with min, fill comparator missing with max
        a_filled = np.where(np.isnan(a), obs_min, a)
        b_filled = np.where(np.isnan(b), obs_max, b)
    else:
        a_filled = np.where(np.isnan(a), obs_max, a)
        b_filled = np.where(np.isnan(b), obs_min, b)
    mean_diff, t_stat, p = _welch(a_filled, b_filled)
    return {
        "type": "worst_case",
        "effect_estimate": mean_diff,
        "p_value": p,
        "t_statistic": t_stat,
        "threshold": None,
        "n_imputed": int(np.sum(np.isnan(a)) + np.sum(np.isnan(b))),
        "note": (
            f"Missing values set to extremes (min={obs_min}, max={obs_max}) "
            f"under direction={direction}."
        ),
    }


def best_case(
    df: pd.DataFrame,
    *,
    outcome: str,
    group: str,
    direction: str = "higher_better",
) -> dict[str, Any]:
    """Best-case: mirror of ``worst_case`` (favourable imputations)."""
    if direction not in ("higher_better", "lower_better"):
        raise ValueError("direction must be 'higher_better' or 'lower_better'")
    a, b = _two_group_arrays(df, outcome, group)
    all_obs = np.concatenate([a[~np.isnan(a)], b[~np.isnan(b)]])
    if all_obs.size == 0:
        raise ValueError("no observed values to derive best-case bounds")
    obs_min, obs_max = float(np.min(all_obs)), float(np.max(all_obs))
    if direction == "higher_better":
        a_filled = np.where(np.isnan(a), obs_max, a)
        b_filled = np.where(np.isnan(b), obs_min, b)
    else:
        a_filled = np.where(np.isnan(a), obs_min, a)
        b_filled = np.where(np.isnan(b), obs_max, b)
    mean_diff, t_stat, p = _welch(a_filled, b_filled)
    return {
        "type": "best_case",
        "effect_estimate": mean_diff,
        "p_value": p,
        "t_statistic": t_stat,
        "threshold": None,
        "n_imputed": int(np.sum(np.isnan(a)) + np.sum(np.isnan(b))),
        "note": (
            f"Missing values set favourably under direction={direction}."
        ),
    }


def tipping_point(
    df: pd.DataFrame,
    *,
    outcome: str,
    group: str,
    candidate_low: float | None = None,
    candidate_high: float | None = None,
    alpha: float = 0.05,
    iterations: int = 50,
) -> dict[str, Any]:
    """Find the imputation value (applied to all missing rows in the FIRST
    group) at which significance flips. Returns ``threshold = None`` when no
    flip is found within the [low, high] range.

    The "first" group is the one that appears first lexicographically in the
    sorted group levels — caller controls which arm receives the candidate
    imputation by relabelling.
    """
    a_arr, b_arr = _two_group_arrays(df, outcome, group)
    all_obs = np.concatenate([a_arr[~np.isnan(a_arr)], b_arr[~np.isnan(b_arr)]])
    if all_obs.size == 0:
        raise ValueError("no observed values to bracket the tipping search")
    lo = float(np.min(all_obs)) if candidate_low is None else float(candidate_low)
    hi = float(np.max(all_obs)) if candidate_high is None else float(candidate_high)
    if not (lo < hi):
        raise ValueError("candidate_low must be < candidate_high")

    n_missing = int(np.sum(np.isnan(a_arr)))

    def _p_at(value: float) -> float:
        a_filled = np.where(np.isnan(a_arr), value, a_arr)
        _, _, p = _welch(a_filled, b_arr)
        return p

    p_lo = _p_at(lo)
    p_hi = _p_at(hi)
    sig_lo = p_lo < alpha
    sig_hi = p_hi < alpha

    if sig_lo == sig_hi:
        return {
            "type": "tipping_point",
            "effect_estimate": None,
            "p_value": None,
            "threshold": None,
            "n_imputed": n_missing,
            "note": (
                f"No flip within [{lo}, {hi}]: p_low={p_lo:.4g}, p_high={p_hi:.4g}."
            ),
        }

    # Bisect.
    for _ in range(iterations):
        mid = 0.5 * (lo + hi)
        sig_mid = _p_at(mid) < alpha
        if sig_mid == sig_lo:
            lo = mid
        else:
            hi = mid
        if abs(hi - lo) < 1e-9:
            break
    threshold = 0.5 * (lo + hi)
    a_filled = np.where(np.isnan(a_arr), threshold, a_arr)
    mean_diff, _, p = _welch(a_filled, b_arr)
    return {
        "type": "tipping_point",
        "effect_estimate": float(mean_diff),
        "p_value": float(p),
        "threshold": float(threshold),
        "n_imputed": n_missing,
        "note": (
            f"Significance flipped at imputation value ≈ {threshold:.4g} "
            f"(alpha={alpha})."
        ),
    }


__all__ = ["worst_case", "best_case", "tipping_point"]
