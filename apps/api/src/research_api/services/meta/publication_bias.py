"""Publication-bias tests (Phase 19 / MP19).

Pure scipy/statsmodels/numpy implementations of:

- Egger's regression test (Egger 1997): linear regression of standardised
  effect on precision (1/SE). Two-sided p of the intercept.
- Harbord's test (Harbord 2006): modified Egger using a binary-outcome
  Z-score and effective sample size, recommended for OR/RR meta-analyses.
- Begg's rank correlation test (Begg 1994): Kendall's τ between
  standardised effect deviations and variances.
- Peters' regression test (Peters 2006): linear regression of log-OR on
  1/(events+non-events) with SE-based weights.

Each returns a ``BiasResult(statistic, p)`` dataclass. ``method`` is set
for clarity in route responses.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

import numpy as np
import statsmodels.api as sm
from scipy import stats


@dataclass(frozen=True)
class BiasResult:
    method: str
    statistic: float
    p: float
    note: str | None = None


def egger_test(effects: Sequence[float], ses: Sequence[float]) -> BiasResult:
    """Egger 1997 regression intercept test for funnel asymmetry."""
    if len(effects) != len(ses):
        raise ValueError("egger_test: effects and ses must have equal length")
    if len(effects) < 3:
        raise ValueError("egger_test: needs at least 3 studies")
    es = np.array(effects, dtype=float)
    s = np.array(ses, dtype=float)
    if np.any(s <= 0):
        raise ValueError("egger_test: SEs must be positive")
    # Snd = effect / se; precision = 1 / se. Regress snd on precision.
    snd = es / s
    precision = 1.0 / s
    design = sm.add_constant(precision)
    fit = sm.OLS(snd, design).fit()
    intercept = float(fit.params[0])
    p = float(fit.pvalues[0])
    return BiasResult(method="egger", statistic=intercept, p=p)


def begg_test(effects: Sequence[float], ses: Sequence[float]) -> BiasResult:
    """Begg 1994 rank-correlation test (Kendall's tau)."""
    if len(effects) != len(ses):
        raise ValueError("begg_test: effects and ses must have equal length")
    if len(effects) < 4:
        raise ValueError("begg_test: needs at least 4 studies")
    es = np.array(effects, dtype=float)
    vis = np.array(ses, dtype=float) ** 2
    if np.any(vis <= 0):
        raise ValueError("begg_test: variances must be positive")
    # Standardise per Begg/Mazumdar: variance-weighted mean removed,
    # then standardise to v* = vi − (1 / Σ(1/vi)).
    weights = 1.0 / vis
    sum_w = float(weights.sum())
    mean_eff = float((weights * es).sum() / sum_w)
    v_star = vis - (1.0 / sum_w)
    # Avoid divide-by-zero if v_star comes out non-positive for some study
    safe_v = np.where(v_star > 0, v_star, np.nan)
    t_i = (es - mean_eff) / np.sqrt(safe_v)
    # Drop NaNs (any pathological per-study v* ≤ 0)
    mask = np.isfinite(t_i)
    t_i = t_i[mask]
    vi_masked = vis[mask]
    if len(t_i) < 4:
        raise ValueError("begg_test: too few usable studies after standardisation")
    tau, p = stats.kendalltau(t_i, vi_masked)
    return BiasResult(method="begg", statistic=float(tau), p=float(p))


def harbord_test(
    events_t: Sequence[int],
    n_t: Sequence[int],
    events_c: Sequence[int],
    n_c: Sequence[int],
) -> BiasResult:
    """Harbord 2006 modified Egger regression for OR/RR meta-analyses.

    Computes per-study Z (score statistic) and V (Fisher information),
    then regresses (Z/sqrt(V)) on sqrt(V) (equivalently regresses on
    precision-adjusted axis). Two-sided p on the intercept.
    """
    arrs = [events_t, n_t, events_c, n_c]
    if not arrs or any(len(a) != len(arrs[0]) for a in arrs):
        raise ValueError("harbord_test: all arrays must have equal length")
    k = len(arrs[0])
    if k < 3:
        raise ValueError("harbord_test: needs at least 3 studies")
    z_vals: list[float] = []
    v_vals: list[float] = []
    for et, nt, ec, nc in zip(events_t, n_t, events_c, n_c):
        et_f, nt_f, ec_f, nc_f = float(et), float(nt), float(ec), float(nc)
        if nt_f <= 0 or nc_f <= 0:
            raise ValueError("harbord_test: group totals must be positive")
        n_total = nt_f + nc_f
        total_events = et_f + ec_f
        expected_t = (nt_f * total_events) / n_total
        # Hypergeometric variance approximation
        if total_events <= 0 or total_events >= n_total:
            # Constant-effect study; contributes no information.
            continue
        v = (
            nt_f * nc_f * total_events * (n_total - total_events)
        ) / (n_total ** 2 * (n_total - 1))
        if v <= 0:
            continue
        z = et_f - expected_t
        z_vals.append(z)
        v_vals.append(v)
    if len(z_vals) < 3:
        raise ValueError("harbord_test: too few informative studies")
    z_arr = np.array(z_vals, dtype=float)
    v_arr = np.array(v_vals, dtype=float)
    snd = z_arr / np.sqrt(v_arr)
    precision = np.sqrt(v_arr)
    design = sm.add_constant(precision)
    fit = sm.OLS(snd, design).fit()
    return BiasResult(
        method="harbord", statistic=float(fit.params[0]), p=float(fit.pvalues[0])
    )


def peters_test(
    events: Sequence[int],
    totals: Sequence[int],
    *,
    log_or: Sequence[float] | None = None,
) -> BiasResult:
    """Peters 2006 regression of log-OR on 1/(events+non-events).

    ``events`` and ``totals`` are per-study aggregated (combined arms).
    ``log_or`` is required — pass log(OR) from each study; the regression
    is weighted by events*(total-events)/total.
    """
    if log_or is None:
        raise ValueError("peters_test: log_or must be provided")
    if not (len(events) == len(totals) == len(log_or)):
        raise ValueError("peters_test: arrays must have equal length")
    k = len(events)
    if k < 3:
        raise ValueError("peters_test: needs at least 3 studies")
    ev = np.array(events, dtype=float)
    tot = np.array(totals, dtype=float)
    if np.any(tot <= 0):
        raise ValueError("peters_test: totals must be positive")
    if np.any(ev < 0) or np.any(ev > tot):
        raise ValueError("peters_test: events must be in [0, total]")
    nonev = tot - ev
    inv_n = 1.0 / tot  # using 1/n as inverse "effective" sample axis
    # Wherever events or non-events are zero, the weight is zero.
    weights = (ev * nonev) / tot
    weights = np.where(weights > 0, weights, np.nan)
    mask = np.isfinite(weights)
    if mask.sum() < 3:
        raise ValueError("peters_test: too few informative studies")
    lo = np.array(log_or, dtype=float)[mask]
    iv = inv_n[mask]
    w = weights[mask]
    design = sm.add_constant(iv)
    fit = sm.WLS(lo, design, weights=w).fit()
    return BiasResult(
        method="peters", statistic=float(fit.params[0]), p=float(fit.pvalues[0])
    )


def select_test_for_metric(metric: str) -> str:
    """Pick the recommended publication-bias test for a meta-analysis metric.

    Maps to the canonical defaults from the Cochrane Handbook chapter 13:
    continuous → Egger; binary OR/RR → Harbord then Peters; rank-based
    fallback → Begg.
    """
    metric = metric.lower()
    if metric in {"md", "smd", "r"}:
        return "egger"
    if metric in {"or", "rr"}:
        return "harbord"
    if metric == "hr":
        return "egger"
    return "egger"


__all__ = [
    "BiasResult",
    "egger_test",
    "begg_test",
    "harbord_test",
    "peters_test",
    "select_test_for_metric",
]
