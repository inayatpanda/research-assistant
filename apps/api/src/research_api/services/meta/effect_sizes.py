"""Per-study effect-size computation for meta-analysis.

All formulae follow Cochrane Handbook v6.3, Ch. 10 conventions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

_Z975 = 1.959964  # two-sided 95% normal quantile


@dataclass(frozen=True)
class Effect:
    """Per-study effect size on the analysis scale.

    For OR/RR/HR, ``yi`` is on the log scale (use :func:`back_transform` to undo).
    For r, ``yi`` is the Fisher-z transform.
    """

    yi: float
    vi: float
    se: float
    metric: str


def md(*, mean_a: float, sd_a: float, n_a: int, mean_b: float, sd_b: float, n_b: int) -> Effect:
    """Mean difference."""
    if n_a < 2 or n_b < 2:
        raise ValueError("MD requires n_a and n_b ≥ 2")
    if sd_a < 0 or sd_b < 0:
        raise ValueError("Standard deviations must be non-negative")
    yi = float(mean_a) - float(mean_b)
    vi = (sd_a ** 2) / n_a + (sd_b ** 2) / n_b
    if vi <= 0:
        raise ValueError("MD variance must be positive")
    return Effect(yi=yi, vi=vi, se=math.sqrt(vi), metric="md")


def smd_hedges_g(
    *, mean_a: float, sd_a: float, n_a: int, mean_b: float, sd_b: float, n_b: int
) -> Effect:
    """Standardised mean difference (Hedges' g, with small-sample correction)."""
    if n_a < 2 or n_b < 2:
        raise ValueError("SMD requires n_a and n_b ≥ 2")
    if sd_a < 0 or sd_b < 0:
        raise ValueError("Standard deviations must be non-negative")
    df = n_a + n_b - 2
    s_p_sq = ((n_a - 1) * sd_a ** 2 + (n_b - 1) * sd_b ** 2) / df
    if s_p_sq <= 0:
        raise ValueError("Pooled SD must be positive (groups appear all-equal)")
    s_p = math.sqrt(s_p_sq)
    d = (mean_a - mean_b) / s_p
    # Hedges' small-sample correction
    j = 1 - 3 / (4 * df - 1)
    g = j * d
    vi = (n_a + n_b) / (n_a * n_b) + (g ** 2) / (2 * (n_a + n_b))
    return Effect(yi=g, vi=vi, se=math.sqrt(vi), metric="smd")


def _continuity_correct(a: int, n_a: int, b: int, n_b: int, k: float = 0.5) -> tuple[float, float, float, float]:
    """Apply +k to all four cells of a 2x2 table iff any cell (incl. non-events) is zero."""
    non_a = n_a - a
    non_b = n_b - b
    if a == 0 or non_a == 0 or b == 0 or non_b == 0:
        return a + k, non_a + k, b + k, non_b + k
    return float(a), float(non_a), float(b), float(non_b)


def odds_ratio(*, events_a: int, n_a: int, events_b: int, n_b: int, continuity: float = 0.5) -> Effect:
    """Log odds ratio with Cochrane-style zero-cell continuity correction."""
    if n_a < 1 or n_b < 1:
        raise ValueError("OR requires n_a and n_b ≥ 1")
    if events_a < 0 or events_b < 0:
        raise ValueError("Events must be non-negative")
    if events_a > n_a or events_b > n_b:
        raise ValueError("events cannot exceed group total")
    a, non_a, b, non_b = _continuity_correct(events_a, n_a, events_b, n_b, k=continuity)
    log_or = math.log((a / non_a) / (b / non_b))
    vi = 1.0 / a + 1.0 / non_a + 1.0 / b + 1.0 / non_b
    return Effect(yi=log_or, vi=vi, se=math.sqrt(vi), metric="or")


def risk_ratio(*, events_a: int, n_a: int, events_b: int, n_b: int, continuity: float = 0.5) -> Effect:
    """Log risk ratio with zero-cell continuity correction."""
    if n_a < 1 or n_b < 1:
        raise ValueError("RR requires n_a and n_b ≥ 1")
    if events_a < 0 or events_b < 0:
        raise ValueError("Events must be non-negative")
    if events_a > n_a or events_b > n_b:
        raise ValueError("events cannot exceed group total")
    a, _non_a, b, _non_b = _continuity_correct(events_a, n_a, events_b, n_b, k=continuity)
    # Note: n's also bumped when continuity kicks in (to keep the 2x2 balanced)
    if events_a == 0 or events_b == 0 or events_a == n_a or events_b == n_b:
        n_a_adj = n_a + 2 * continuity
        n_b_adj = n_b + 2 * continuity
    else:
        n_a_adj = float(n_a)
        n_b_adj = float(n_b)
    p_a = a / n_a_adj
    p_b = b / n_b_adj
    log_rr = math.log(p_a / p_b)
    vi = 1.0 / a - 1.0 / n_a_adj + 1.0 / b - 1.0 / n_b_adj
    if vi <= 0:
        # extremely rare numerical edge — bump up
        vi = abs(vi) + 1e-9
    return Effect(yi=log_rr, vi=vi, se=math.sqrt(vi), metric="rr")


def hazard_ratio_from_logs(*, log_hr: float, se_log_hr: float) -> Effect:
    """HR effect from a published log_hr + se. The most direct path when authors report them."""
    if se_log_hr <= 0:
        raise ValueError("se_log_hr must be positive")
    vi = se_log_hr ** 2
    return Effect(yi=float(log_hr), vi=vi, se=float(se_log_hr), metric="hr")


def hazard_ratio_from_ci(*, hr: float, hr_ci_low: float, hr_ci_high: float) -> Effect:
    """HR effect when researchers transcribe HR + 95% CI from a paper."""
    if hr <= 0 or hr_ci_low <= 0 or hr_ci_high <= 0:
        raise ValueError("HR and its CI bounds must be positive")
    if not (hr_ci_low < hr_ci_high):
        raise ValueError("hr_ci_low must be < hr_ci_high")
    log_hr = math.log(hr)
    se = (math.log(hr_ci_high) - math.log(hr_ci_low)) / (2 * _Z975)
    if se <= 0:
        raise ValueError("CI width gives non-positive SE")
    return Effect(yi=log_hr, vi=se ** 2, se=se, metric="hr")


def correlation_fisher_z(*, r: float, n: int) -> Effect:
    """Pearson r via Fisher's z transform."""
    if n < 4:
        raise ValueError("Fisher-z requires n ≥ 4")
    if not (-1.0 < r < 1.0):
        raise ValueError("r must be strictly inside (-1, 1)")
    z = math.atanh(r)
    vi = 1.0 / (n - 3)
    return Effect(yi=z, vi=vi, se=math.sqrt(vi), metric="r")


def back_transform(metric: str, yi: float) -> float:
    """Undo the analysis-scale transform applied at study level.

    md / smd → passthrough.
    or / rr / hr → exp(yi).
    r → tanh(yi)  (Fisher's z inverse).
    """
    m = metric.lower()
    if m in {"md", "smd"}:
        return float(yi)
    if m in {"or", "rr", "hr"}:
        return math.exp(yi)
    if m == "r":
        return math.tanh(yi)
    raise ValueError(f"unknown metric: {metric!r}")
