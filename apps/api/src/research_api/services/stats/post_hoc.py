"""Phase 17 (MP17) — Post-hoc pairwise comparison procedures.

All four functions take a ``groups: dict[label, list[float]]`` (2+ groups)
and return ``list[dict]`` rows shaped::

  {pair: ("A", "B"), mean_diff: 1.23, ci_low: 0.5, ci_high: 1.96, p_adj: 0.01,
   n_a: 30, n_b: 32}

This module is pure (no I/O). The data-loader is the runner's responsibility.
"""
from __future__ import annotations

import math
from itertools import combinations
from typing import Any

import numpy as np
from scipy import stats


def _validate(groups: dict[str, list[float]], *, min_groups: int = 2) -> None:
    if not isinstance(groups, dict):
        raise ValueError("groups must be a dict[label, list[float]]")
    if len(groups) < min_groups:
        raise ValueError(f"need >= {min_groups} groups; got {len(groups)}")
    for k, v in groups.items():
        if not isinstance(k, str):
            raise ValueError("group labels must be strings")
        if len(v) < 2:
            raise ValueError(f"group {k!r} has < 2 observations")


def tukey_hsd(groups: dict[str, list[float]]) -> list[dict[str, Any]]:
    """Tukey HSD pairwise comparisons via statsmodels ``pairwise_tukeyhsd``.

    Assumes homoscedasticity. The studentised-range distribution yields the
    confidence interval; ``p_adj`` is the family-wise adjusted p-value.
    """
    from statsmodels.stats.multicomp import pairwise_tukeyhsd

    _validate(groups)
    labels: list[str] = []
    values: list[float] = []
    for k, vs in groups.items():
        labels.extend([k] * len(vs))
        values.extend(vs)
    res = pairwise_tukeyhsd(endog=np.asarray(values, dtype=float), groups=np.asarray(labels))
    rows: list[dict[str, Any]] = []
    summary_table = res._results_table.data[1:]  # type: ignore[attr-defined]
    for row in summary_table:
        g1, g2, mean_diff, p_adj, ci_low, ci_high, _ = row
        rows.append(
            {
                "pair": (str(g1), str(g2)),
                "mean_diff": float(mean_diff),
                "ci_low": float(ci_low),
                "ci_high": float(ci_high),
                "p_adj": float(p_adj),
                "n_a": len(groups[str(g1)]),
                "n_b": len(groups[str(g2)]),
                "method": "tukey_hsd",
            }
        )
    return rows


def bonferroni_pairwise(groups: dict[str, list[float]]) -> list[dict[str, Any]]:
    """Bonferroni-adjusted pairwise t-tests (Welch). Pools nothing — independent
    Welch t-tests, multiplied raw-p by the number of pairwise comparisons."""
    _validate(groups)
    keys = sorted(groups.keys())
    pairs = list(combinations(keys, 2))
    n_comp = len(pairs)
    rows: list[dict[str, Any]] = []
    for a, b in pairs:
        x = np.asarray(groups[a], dtype=float)
        y = np.asarray(groups[b], dtype=float)
        t_stat, p_raw = stats.ttest_ind(x, y, equal_var=False)
        mean_diff = float(np.mean(x) - np.mean(y))
        # Welch SE for CI.
        s2_x = float(np.var(x, ddof=1))
        s2_y = float(np.var(y, ddof=1))
        n_x, n_y = len(x), len(y)
        se = math.sqrt(s2_x / n_x + s2_y / n_y)
        # Welch–Satterthwaite df for CI t-quantile.
        if se > 0:
            df_w = (s2_x / n_x + s2_y / n_y) ** 2 / (
                (s2_x / n_x) ** 2 / (n_x - 1) + (s2_y / n_y) ** 2 / (n_y - 1)
            )
        else:
            df_w = float(n_x + n_y - 2)
        # Bonferroni-corrected alpha for the 95% CI.
        alpha_adj = 0.05 / n_comp
        t_crit = float(stats.t.ppf(1 - alpha_adj / 2, df_w))
        rows.append(
            {
                "pair": (a, b),
                "mean_diff": mean_diff,
                "ci_low": mean_diff - t_crit * se,
                "ci_high": mean_diff + t_crit * se,
                "p_adj": float(min(1.0, p_raw * n_comp)),
                "n_a": n_x,
                "n_b": n_y,
                "method": "bonferroni",
            }
        )
    return rows


def dunns_test(groups: dict[str, list[float]]) -> list[dict[str, Any]]:
    """Dunn's test — rank-based pairwise comparison after Kruskal-Wallis.

    Tie correction follows Dunn (1964). p-values are Bonferroni-adjusted
    (the most common follow-up convention).
    """
    _validate(groups)
    keys = sorted(groups.keys())
    sizes = {k: len(groups[k]) for k in keys}
    all_values: list[float] = []
    group_labels: list[str] = []
    for k in keys:
        all_values.extend(groups[k])
        group_labels.extend([k] * sizes[k])
    N = len(all_values)
    ranks = stats.rankdata(all_values, method="average")
    # Mean rank per group.
    mean_rank = {}
    pos = 0
    for k in keys:
        mean_rank[k] = float(np.mean(ranks[pos : pos + sizes[k]]))
        pos += sizes[k]
    # Tie correction.
    _, tie_counts = np.unique(all_values, return_counts=True)
    tie_corr = float(np.sum(tie_counts**3 - tie_counts))
    var_base = (N * (N + 1) / 12.0) - tie_corr / (12.0 * (N - 1)) if N > 1 else 0.0

    pairs = list(combinations(keys, 2))
    n_comp = len(pairs)
    rows: list[dict[str, Any]] = []
    for a, b in pairs:
        diff = mean_rank[a] - mean_rank[b]
        se = math.sqrt(var_base * (1.0 / sizes[a] + 1.0 / sizes[b])) if var_base > 0 else float("nan")
        if se > 0:
            z = diff / se
            p_raw = 2.0 * (1.0 - stats.norm.cdf(abs(z)))
        else:
            z, p_raw = float("nan"), float("nan")
        p_adj = float(min(1.0, p_raw * n_comp)) if not math.isnan(p_raw) else float("nan")
        rows.append(
            {
                "pair": (a, b),
                "mean_diff": float(diff),
                "ci_low": None,
                "ci_high": None,
                "p_adj": p_adj,
                "z_statistic": float(z) if not math.isnan(z) else None,
                "n_a": sizes[a],
                "n_b": sizes[b],
                "method": "dunns",
            }
        )
    return rows


def games_howell(groups: dict[str, list[float]]) -> list[dict[str, Any]]:
    """Games-Howell — pairwise comparison that does NOT assume equal variance.

    Uses the studentised-range distribution with Welch-Satterthwaite df.
    """
    from statsmodels.stats.libqsturng import psturng, qsturng

    _validate(groups)
    keys = sorted(groups.keys())
    means = {k: float(np.mean(groups[k])) for k in keys}
    vars_ = {k: float(np.var(groups[k], ddof=1)) for k in keys}
    ns = {k: len(groups[k]) for k in keys}
    k_groups = len(keys)
    pairs = list(combinations(keys, 2))
    rows: list[dict[str, Any]] = []
    for a, b in pairs:
        diff = means[a] - means[b]
        se = math.sqrt((vars_[a] / ns[a] + vars_[b] / ns[b]) / 2.0)
        if se <= 0:
            rows.append(
                {
                    "pair": (a, b),
                    "mean_diff": float(diff),
                    "ci_low": None,
                    "ci_high": None,
                    "p_adj": float("nan"),
                    "method": "games_howell",
                    "n_a": ns[a],
                    "n_b": ns[b],
                }
            )
            continue
        df_w = ((vars_[a] / ns[a] + vars_[b] / ns[b]) ** 2) / (
            (vars_[a] / ns[a]) ** 2 / (ns[a] - 1)
            + (vars_[b] / ns[b]) ** 2 / (ns[b] - 1)
        )
        q = abs(diff) / se
        # studentised range survival fn — psturng returns the upper-tail probability
        try:
            p_adj = float(psturng(q, k_groups, df_w))
        except Exception:
            p_adj = float("nan")
        try:
            q_crit = float(qsturng(0.95, k_groups, df_w))
        except Exception:
            q_crit = float("nan")
        ci_half = q_crit * se if not math.isnan(q_crit) else float("nan")
        rows.append(
            {
                "pair": (a, b),
                "mean_diff": float(diff),
                "ci_low": float(diff - ci_half) if not math.isnan(ci_half) else None,
                "ci_high": float(diff + ci_half) if not math.isnan(ci_half) else None,
                "p_adj": float(min(1.0, p_adj)) if not math.isnan(p_adj) else float("nan"),
                "df": float(df_w),
                "n_a": ns[a],
                "n_b": ns[b],
                "method": "games_howell",
            }
        )
    return rows


__all__ = [
    "tukey_hsd",
    "bonferroni_pairwise",
    "dunns_test",
    "games_howell",
]
