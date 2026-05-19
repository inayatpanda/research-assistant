"""Phase 13 — Pre-study sample-size + power calculator.

Pure-function wrappers around ``statsmodels.stats.power`` plus a hand-rolled
Fisher-z correlation solver. Each public function returns:

  {
    "required_n": int,
    "required_n_per_group": int | None,
    "alpha": float,
    "power": float,
    "effect_size": float,
    "sensitivity_curve_png": bytes,
    "notes": str,
  }

The sensitivity curve sweeps sample size around the required-n point and
plots achieved power vs sample size with the requested alpha and effect
size. Matplotlib uses the global Agg backend pinned in
``services.stats.charts._base``; we re-pin here for safety because this
module is callable without the charts package being imported first.
"""
from __future__ import annotations

import math
from typing import Any

import matplotlib

matplotlib.use("Agg")  # MUST come before pyplot import.
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from io import BytesIO  # noqa: E402
from scipy import stats as sp_stats  # noqa: E402
from statsmodels.stats.power import (  # noqa: E402
    FTestAnovaPower,
    GofChisquarePower,
    TTestIndPower,
    TTestPower,
)

_DPI = 130
_FIGSIZE = (6.5, 4.0)


def _ceil_pos(value: float, minimum: int = 2) -> int:
    if value is None or not math.isfinite(value) or value <= 0:
        return minimum
    return max(int(math.ceil(value)), minimum)


def _sensitivity_curve_png(
    *,
    xs: list[int],
    powers: list[float],
    required_n: int,
    target_power: float,
    title: str,
    x_label: str,
) -> bytes:
    fig = plt.figure(figsize=_FIGSIZE, dpi=_DPI)
    try:
        ax = fig.add_subplot(1, 1, 1)
        ax.plot(xs, powers, color="#3b82f6", linewidth=2)
        ax.axhline(target_power, color="#9ca3af", linestyle="--", linewidth=1, label=f"target power = {target_power:.2f}")
        ax.axvline(required_n, color="#ef4444", linestyle="--", linewidth=1, label=f"required n = {required_n}")
        ax.set_xlabel(x_label)
        ax.set_ylabel("Achieved power")
        ax.set_ylim(0.0, 1.02)
        ax.set_title(title)
        ax.legend(loc="lower right")
        ax.grid(True, alpha=0.3)
        buf = BytesIO()
        fig.savefig(buf, format="png", dpi=_DPI, bbox_inches="tight")
        return buf.getvalue()
    finally:
        plt.close(fig)


def _validate_alpha_power(alpha: float, power: float) -> None:
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1)")
    if not (0 < power < 1):
        raise ValueError("power must be in (0, 1)")


def _validate_effect_size(effect_size: float) -> None:
    if not math.isfinite(effect_size) or effect_size <= 0:
        raise ValueError("effect_size must be a positive finite number")


def power_ttest_ind(
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> dict[str, Any]:
    """Independent two-sample t-test power calc (Cohen's d).

    Returns required n PER GROUP. The total trial size is 2 * n_per_group.
    """
    _validate_effect_size(effect_size)
    _validate_alpha_power(alpha, power)
    solver = TTestIndPower()
    n_per_group = solver.solve_power(
        effect_size=effect_size, alpha=alpha, power=power, ratio=1.0, alternative="two-sided"
    )
    n_per_group_int = _ceil_pos(n_per_group)
    xs = list(range(max(5, n_per_group_int // 4), n_per_group_int * 2 + 1))
    powers = [
        float(solver.power(effect_size=effect_size, nobs1=n, alpha=alpha, ratio=1.0, alternative="two-sided"))
        for n in xs
    ]
    png = _sensitivity_curve_png(
        xs=xs,
        powers=powers,
        required_n=n_per_group_int,
        target_power=power,
        title=f"Two-sample t-test power (d={effect_size}, alpha={alpha})",
        x_label="n per group",
    )
    return {
        "required_n": n_per_group_int * 2,
        "required_n_per_group": n_per_group_int,
        "alpha": alpha,
        "power": power,
        "effect_size": effect_size,
        "sensitivity_curve_png": png,
        "notes": (
            f"Cohen's d = {effect_size}. Required {n_per_group_int} per group "
            f"(total {n_per_group_int * 2}) for power = {power:.2f} at alpha = {alpha:.3f}."
        ),
    }


def power_ttest_paired(
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> dict[str, Any]:
    """Paired t-test power calc (Cohen's dz). Returns required total n (pairs)."""
    _validate_effect_size(effect_size)
    _validate_alpha_power(alpha, power)
    solver = TTestPower()
    n_pairs = solver.solve_power(
        effect_size=effect_size, alpha=alpha, power=power, alternative="two-sided"
    )
    n_pairs_int = _ceil_pos(n_pairs)
    xs = list(range(max(5, n_pairs_int // 4), n_pairs_int * 2 + 1))
    powers = [
        float(solver.power(effect_size=effect_size, nobs=n, alpha=alpha, alternative="two-sided"))
        for n in xs
    ]
    png = _sensitivity_curve_png(
        xs=xs,
        powers=powers,
        required_n=n_pairs_int,
        target_power=power,
        title=f"Paired t-test power (dz={effect_size}, alpha={alpha})",
        x_label="n pairs",
    )
    return {
        "required_n": n_pairs_int,
        "required_n_per_group": None,
        "alpha": alpha,
        "power": power,
        "effect_size": effect_size,
        "sensitivity_curve_png": png,
        "notes": (
            f"Cohen's dz = {effect_size}. Required {n_pairs_int} pairs for "
            f"power = {power:.2f} at alpha = {alpha:.3f}."
        ),
    }


def power_anova(
    effect_size: float,
    k_groups: int,
    alpha: float = 0.05,
    power: float = 0.80,
) -> dict[str, Any]:
    """One-way ANOVA power calc (Cohen's f). Returns total n and n per group."""
    _validate_effect_size(effect_size)
    _validate_alpha_power(alpha, power)
    if not isinstance(k_groups, int) or k_groups < 2:
        raise ValueError("k_groups must be an integer >= 2")
    solver = FTestAnovaPower()
    nobs_total = solver.solve_power(
        effect_size=effect_size, k_groups=k_groups, alpha=alpha, power=power
    )
    n_total_int = _ceil_pos(nobs_total, minimum=k_groups * 2)
    n_per_group = int(math.ceil(n_total_int / k_groups))
    # Round up to a balanced design.
    n_total_balanced = n_per_group * k_groups
    xs_per = list(range(max(3, n_per_group // 4), n_per_group * 2 + 1))
    powers = [
        float(solver.power(effect_size=effect_size, nobs=n * k_groups, k_groups=k_groups, alpha=alpha))
        for n in xs_per
    ]
    png = _sensitivity_curve_png(
        xs=xs_per,
        powers=powers,
        required_n=n_per_group,
        target_power=power,
        title=f"One-way ANOVA power (f={effect_size}, k={k_groups}, alpha={alpha})",
        x_label="n per group",
    )
    return {
        "required_n": n_total_balanced,
        "required_n_per_group": n_per_group,
        "alpha": alpha,
        "power": power,
        "effect_size": effect_size,
        "sensitivity_curve_png": png,
        "notes": (
            f"Cohen's f = {effect_size}, k = {k_groups}. Required "
            f"{n_per_group} per group (total {n_total_balanced}) for "
            f"power = {power:.2f} at alpha = {alpha:.3f}."
        ),
    }


def power_chi_square(
    effect_size: float,
    df: int,
    alpha: float = 0.05,
    power: float = 0.80,
) -> dict[str, Any]:
    """Chi-square goodness-of-fit power calc (Cohen's w). df = bins - 1."""
    _validate_effect_size(effect_size)
    _validate_alpha_power(alpha, power)
    if not isinstance(df, int) or df < 1:
        raise ValueError("df must be a positive integer (df = bins - 1)")
    solver = GofChisquarePower()
    n_bins = df + 1
    n_total = solver.solve_power(
        effect_size=effect_size, alpha=alpha, power=power, n_bins=n_bins
    )
    n_total_int = _ceil_pos(n_total)
    xs = list(range(max(5, n_total_int // 4), n_total_int * 2 + 1))
    powers = [
        float(solver.power(effect_size=effect_size, nobs=n, alpha=alpha, n_bins=n_bins))
        for n in xs
    ]
    png = _sensitivity_curve_png(
        xs=xs,
        powers=powers,
        required_n=n_total_int,
        target_power=power,
        title=f"Chi-square GoF power (w={effect_size}, df={df}, alpha={alpha})",
        x_label="total n",
    )
    return {
        "required_n": n_total_int,
        "required_n_per_group": None,
        "alpha": alpha,
        "power": power,
        "effect_size": effect_size,
        "sensitivity_curve_png": png,
        "notes": (
            f"Cohen's w = {effect_size}, df = {df}. Required {n_total_int} "
            f"total observations for power = {power:.2f} at alpha = {alpha:.3f}."
        ),
    }


def _correlation_required_n(r: float, alpha: float, power: float) -> float:
    """Solve required n via Fisher z transformation (two-sided test)."""
    if abs(r) >= 1:
        raise ValueError("|r| must be < 1")
    z_r = math.atanh(abs(r))
    z_alpha = sp_stats.norm.ppf(1 - alpha / 2)
    z_beta = sp_stats.norm.ppf(power)
    n_minus_3 = ((z_alpha + z_beta) / z_r) ** 2
    return n_minus_3 + 3.0


def _correlation_power_at(r: float, n: int, alpha: float) -> float:
    """Achieved power at a given n via inverse Fisher-z formula."""
    if n <= 3:
        return float("nan")
    z_r = math.atanh(abs(r))
    z_alpha = sp_stats.norm.ppf(1 - alpha / 2)
    z_stat = z_r * math.sqrt(n - 3)
    return float(sp_stats.norm.cdf(z_stat - z_alpha) + sp_stats.norm.cdf(-z_stat - z_alpha))


def power_correlation(
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> dict[str, Any]:
    """Pearson r power calc via Fisher z transformation. Returns total n."""
    _validate_effect_size(effect_size)
    _validate_alpha_power(alpha, power)
    if abs(effect_size) >= 1:
        raise ValueError("correlation effect_size must satisfy |r| < 1")
    n_total = _correlation_required_n(effect_size, alpha, power)
    n_total_int = _ceil_pos(n_total, minimum=4)
    xs = list(range(max(5, n_total_int // 4), n_total_int * 2 + 1))
    powers = [_correlation_power_at(effect_size, n, alpha) for n in xs]
    png = _sensitivity_curve_png(
        xs=xs,
        powers=powers,
        required_n=n_total_int,
        target_power=power,
        title=f"Pearson correlation power (r={effect_size}, alpha={alpha})",
        x_label="total n",
    )
    return {
        "required_n": n_total_int,
        "required_n_per_group": None,
        "alpha": alpha,
        "power": power,
        "effect_size": effect_size,
        "sensitivity_curve_png": png,
        "notes": (
            f"Pearson r = {effect_size}. Fisher z transformation. Required "
            f"{n_total_int} observations for power = {power:.2f} at alpha = {alpha:.3f}."
        ),
    }


# ─── Phase 17 (MP17) — Extended power families ─────────────────────────────


def power_logrank(
    hazard_ratio: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
    allocation_ratio: float = 1.0,
    event_rate: float = 0.5,
) -> dict[str, Any]:
    """Log-rank required total N for a two-arm survival comparison.

    Uses Schoenfeld's formula:

        d = (z_{1-α/2} + z_{1-β})² · (1 + k)² / (k · ln(HR)²)

    where ``k = allocation_ratio = n_treatment / n_control`` and ``d`` is the
    required total number of EVENTS. Total ``N`` is then ``d / event_rate``.

    ``hazard_ratio`` must be != 1 (it would imply no effect to detect).
    """
    if not math.isfinite(hazard_ratio) or hazard_ratio <= 0 or hazard_ratio == 1.0:
        raise ValueError("hazard_ratio must be > 0 and != 1")
    _validate_alpha_power(alpha, power)
    if not (0 < event_rate <= 1):
        raise ValueError("event_rate must be in (0, 1]")
    if allocation_ratio <= 0:
        raise ValueError("allocation_ratio must be > 0")
    z_a = float(sp_stats.norm.ppf(1 - alpha / 2))
    z_b = float(sp_stats.norm.ppf(power))
    log_hr = math.log(hazard_ratio)
    k = float(allocation_ratio)
    required_events = ((z_a + z_b) ** 2) * ((1 + k) ** 2) / (k * (log_hr**2))
    required_events_int = _ceil_pos(required_events, minimum=4)
    n_total = required_events_int / event_rate
    n_total_int = _ceil_pos(n_total, minimum=4)
    # Sensitivity curve over total sample size at fixed HR.
    xs = list(range(max(8, n_total_int // 4), n_total_int * 2 + 1))
    powers: list[float] = []
    for n in xs:
        d = n * event_rate
        if d <= 0:
            powers.append(0.0)
            continue
        # invert Schoenfeld at this d to get achieved power
        rhs = math.sqrt(d * k / ((1 + k) ** 2)) * abs(log_hr) - z_a
        powers.append(float(sp_stats.norm.cdf(rhs)))
    png = _sensitivity_curve_png(
        xs=xs,
        powers=powers,
        required_n=n_total_int,
        target_power=power,
        title=f"Log-rank power (HR={hazard_ratio}, event_rate={event_rate})",
        x_label="total n",
    )
    return {
        "required_n": n_total_int,
        "required_n_per_group": int(math.ceil(n_total_int / (1 + k))),
        "required_events": required_events_int,
        "alpha": alpha,
        "power": power,
        "effect_size": float(hazard_ratio),
        "sensitivity_curve_png": png,
        "notes": (
            f"Schoenfeld log-rank: HR={hazard_ratio}, event_rate={event_rate}. "
            f"Required {required_events_int} events and ~{n_total_int} total "
            f"participants for power={power:.2f} at alpha={alpha:.3f}."
        ),
    }


def power_mixed_effects(
    effect_size: float,
    *,
    n_per_cluster: int,
    n_clusters: int,
    icc: float,
    alpha: float = 0.05,
    power: float = 0.80,
) -> dict[str, Any]:
    """Cluster-RCT design-effect correction for a continuous outcome.

    Given a planned ``n_clusters`` × ``n_per_cluster`` design and intra-class
    correlation ``icc``, the effective sample size is

        n_eff = N / DE        with DE = 1 + (n_per_cluster - 1) · ICC.

    We solve the two-sample ``t``-test required n_per_group from Cohen's d,
    multiply by DE, then return the required *total* sample size to achieve
    the planned cluster size.
    """
    _validate_effect_size(effect_size)
    _validate_alpha_power(alpha, power)
    if not (0 <= icc <= 1):
        raise ValueError("icc must be in [0, 1]")
    if n_per_cluster < 1:
        raise ValueError("n_per_cluster must be >= 1")
    if n_clusters < 2:
        raise ValueError("n_clusters must be >= 2")
    de = 1.0 + (n_per_cluster - 1) * icc
    # Required n per group ignoring clustering.
    solver = TTestIndPower()
    n_per_group_indep = solver.solve_power(
        effect_size=effect_size, alpha=alpha, power=power, ratio=1.0, alternative="two-sided"
    )
    n_per_group_clustered = n_per_group_indep * de
    n_per_group_int = _ceil_pos(n_per_group_clustered)
    n_total = n_per_group_int * 2
    # Required clusters per arm.
    required_clusters_per_arm = math.ceil(n_per_group_int / n_per_cluster)
    xs = list(range(max(5, n_per_group_int // 4), n_per_group_int * 2 + 1))
    powers = [
        float(
            solver.power(
                effect_size=effect_size,
                nobs1=n / de,
                alpha=alpha,
                ratio=1.0,
                alternative="two-sided",
            )
        )
        for n in xs
    ]
    png = _sensitivity_curve_png(
        xs=xs,
        powers=powers,
        required_n=n_per_group_int,
        target_power=power,
        title=f"Cluster RCT power (d={effect_size}, ICC={icc}, m={n_per_cluster})",
        x_label="n per arm (clustered)",
    )
    return {
        "required_n": n_total,
        "required_n_per_group": n_per_group_int,
        "required_clusters_per_arm": int(required_clusters_per_arm),
        "design_effect": float(de),
        "alpha": alpha,
        "power": power,
        "effect_size": effect_size,
        "sensitivity_curve_png": png,
        "notes": (
            f"Cluster RCT: d={effect_size}, ICC={icc}, cluster size={n_per_cluster}, "
            f"design effect={de:.3f}. Required {n_per_group_int} per arm "
            f"(~{required_clusters_per_arm} clusters per arm) for power={power:.2f}."
        ),
    }


def power_noninferiority(
    margin: float,
    *,
    sigma: float,
    alpha: float = 0.025,
    power: float = 0.80,
    allocation_ratio: float = 1.0,
) -> dict[str, Any]:
    """Non-inferiority sample size (one-sided test of mean diff vs margin).

    Required N per arm = (z_{1-α} + z_{1-β})² · σ² · (1 + 1/k) / margin²

    where ``margin`` is positive and on the same scale as ``sigma``.
    The default ``alpha=0.025`` mirrors the FDA convention of a one-sided
    2.5% level (equivalent to two-sided 5%).
    """
    if margin <= 0 or not math.isfinite(margin):
        raise ValueError("margin must be > 0")
    if sigma <= 0 or not math.isfinite(sigma):
        raise ValueError("sigma must be > 0")
    if not (0 < alpha < 1):
        raise ValueError("alpha must be in (0, 1)")
    if not (0 < power < 1):
        raise ValueError("power must be in (0, 1)")
    if allocation_ratio <= 0:
        raise ValueError("allocation_ratio must be > 0")
    z_a = float(sp_stats.norm.ppf(1 - alpha))
    z_b = float(sp_stats.norm.ppf(power))
    k = float(allocation_ratio)
    n_per_arm = ((z_a + z_b) ** 2) * (sigma**2) * (1.0 + 1.0 / k) / (margin**2)
    n_per_arm_int = _ceil_pos(n_per_arm)
    n_total = n_per_arm_int + math.ceil(n_per_arm_int * k)
    xs = list(range(max(5, n_per_arm_int // 4), n_per_arm_int * 2 + 1))
    powers: list[float] = []
    for n in xs:
        # invert: with n per arm, achieved power for the same margin/sigma
        se = sigma * math.sqrt((1.0 + 1.0 / k) / n)
        rhs = (margin / se) - z_a
        powers.append(float(sp_stats.norm.cdf(rhs)))
    png = _sensitivity_curve_png(
        xs=xs,
        powers=powers,
        required_n=n_per_arm_int,
        target_power=power,
        title=f"Non-inferiority power (margin={margin}, σ={sigma})",
        x_label="n per arm",
    )
    return {
        "required_n": n_total,
        "required_n_per_group": n_per_arm_int,
        "alpha": alpha,
        "power": power,
        "effect_size": float(margin),
        "sensitivity_curve_png": png,
        "notes": (
            f"Non-inferiority (one-sided alpha={alpha}). Required {n_per_arm_int} "
            f"per arm (total {n_total}) for power={power:.2f}."
        ),
    }


__all__ = [
    "power_ttest_ind",
    "power_ttest_paired",
    "power_anova",
    "power_chi_square",
    "power_correlation",
    "power_logrank",
    "power_mixed_effects",
    "power_noninferiority",
]


# Suppress unused-import warning for numpy in some environments.
_ = np
