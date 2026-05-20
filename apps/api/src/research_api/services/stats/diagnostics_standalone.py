"""DEMO-FIX-A — Standalone diagnostic-test service.

This module exposes plain functions (no I/O, no dataset model coupling) that
compute the diagnostics a researcher needs *before* picking a statistical
test:

  * normality (Shapiro-Wilk, Anderson-Darling, Kolmogorov-Smirnov,
    D'Agostino-Pearson)
  * equality of variance across groups (Levene with the Brown-Forsythe
    median-centred variant, Bartlett)
  * visual checks (Q-Q against the normal, histogram with a fitted normal
    curve)

These mirror the assumption checks that already run automatically alongside
parametric tests in ``runner.py`` — but the user can now run them
independently and pick which variant they want.

The ``interpretation`` field in each return dict is a single sentence
written for a clinical-research audience.  When the assumption fails, the
sentence also suggests a next step (e.g. switch to Mann-Whitney, use a
log transform).  This is the "test-recommendation logic" referenced in
the demo-fix scope.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats

ALPHA = 0.05


def _to_array(values: list[float] | np.ndarray) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[~np.isnan(arr)]
    return arr


def _fmt_p(p: float) -> str:
    if not np.isfinite(p):
        return "nan"
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


# ── Normality tests ────────────────────────────────────────────────────


def shapiro_wilk(values: list[float] | np.ndarray) -> dict[str, Any]:
    """Shapiro-Wilk normality test.

    Returns ``{statistic, p, n, interpretation}``.  Recommends a
    non-parametric alternative when the null is rejected.
    """
    arr = _to_array(values)
    n = int(arr.size)
    if n < 3:
        raise ValueError("Shapiro-Wilk requires at least 3 non-missing values")
    if n > 5000:
        arr = np.random.default_rng(0).choice(arr, size=5000, replace=False)
    stat, p = stats.shapiro(arr)
    p = float(p)
    stat = float(stat)
    if p > ALPHA:
        interpretation = (
            f"Sample is consistent with a normal distribution "
            f"(Shapiro-Wilk W={stat:.4f}, p={_fmt_p(p)} > {ALPHA}); "
            f"parametric tests (t-test, ANOVA, Pearson) are appropriate."
        )
    else:
        interpretation = (
            f"Strong evidence against normality "
            f"(Shapiro-Wilk W={stat:.4f}, p={_fmt_p(p)} < {ALPHA}); "
            f"consider a non-parametric alternative such as Mann-Whitney, "
            f"Wilcoxon signed-rank, Kruskal-Wallis, or Spearman correlation."
        )
    return {"statistic": stat, "p": p, "n": n, "interpretation": interpretation}


def anderson_darling(values: list[float] | np.ndarray) -> dict[str, Any]:
    """Anderson-Darling normality test (no exact p-value — uses critical
    values).  The interpretation cites the 5% critical value.
    """
    arr = _to_array(values)
    n = int(arr.size)
    if n < 8:
        raise ValueError("Anderson-Darling requires at least 8 non-missing values")
    res = stats.anderson(arr, dist="norm")
    stat = float(res.statistic)
    # ``critical_values`` line up with ``significance_level`` (in percent).
    crit_pct = list(res.significance_level)
    crit_vals = list(res.critical_values)
    crit_dict = {f"{int(p)}%": float(v) for p, v in zip(crit_pct, crit_vals)}
    # 5% is the canonical comparison point.
    crit_5 = float(crit_dict.get("5%", crit_vals[2]))
    if stat <= crit_5:
        interpretation = (
            f"Sample is consistent with a normal distribution "
            f"(Anderson-Darling A²={stat:.4f} ≤ 5% critical value {crit_5:.4f}); "
            f"parametric tests are appropriate."
        )
    else:
        interpretation = (
            f"Departure from normality detected "
            f"(Anderson-Darling A²={stat:.4f} > 5% critical value {crit_5:.4f}); "
            f"consider a non-parametric alternative or check for outliers / "
            f"a transformation such as log."
        )
    return {
        "statistic": stat,
        "critical_values": crit_dict,
        "significance_levels": [float(p) for p in crit_pct],
        "n": n,
        "interpretation": interpretation,
    }


def kolmogorov_smirnov(
    values: list[float] | np.ndarray, distribution: str = "norm"
) -> dict[str, Any]:
    """One-sample KS test against the normal (mean and SD estimated from
    the data).

    Note: estimating the parameters from the same sample inflates p-values
    relative to the true KS distribution (this is the well-known Lilliefors
    issue).  We still report the standard KS statistic and surface the
    caveat in the interpretation when the result is borderline.
    """
    arr = _to_array(values)
    n = int(arr.size)
    if n < 3:
        raise ValueError("KS test requires at least 3 non-missing values")
    if distribution != "norm":
        raise ValueError("only 'norm' is supported for now")
    mu = float(arr.mean())
    sd = float(arr.std(ddof=1))
    if not np.isfinite(sd) or sd <= 0:
        raise ValueError("KS test requires positive sample standard deviation")
    stat, p = stats.kstest(arr, "norm", args=(mu, sd))
    stat = float(stat)
    p = float(p)
    if p > ALPHA:
        interpretation = (
            f"Sample is consistent with a normal distribution "
            f"(KS D={stat:.4f}, p={_fmt_p(p)} > {ALPHA}); "
            f"note that estimating μ and σ from the sample inflates p — "
            f"prefer Shapiro-Wilk for small samples."
        )
    else:
        interpretation = (
            f"Departure from normality detected "
            f"(KS D={stat:.4f}, p={_fmt_p(p)} < {ALPHA}); "
            f"consider a non-parametric alternative."
        )
    return {"statistic": stat, "p": p, "n": n, "interpretation": interpretation}


def dagostino_pearson(values: list[float] | np.ndarray) -> dict[str, Any]:
    """D'Agostino-Pearson K² omnibus normality test (skew + kurtosis)."""
    arr = _to_array(values)
    n = int(arr.size)
    if n < 8:
        raise ValueError(
            "D'Agostino-Pearson requires at least 8 non-missing values"
        )
    stat, p = stats.normaltest(arr)
    stat = float(stat)
    p = float(p)
    if p > ALPHA:
        interpretation = (
            f"Sample is consistent with a normal distribution "
            f"(D'Agostino K²={stat:.4f}, p={_fmt_p(p)} > {ALPHA})."
        )
    else:
        interpretation = (
            f"Strong evidence against normality "
            f"(D'Agostino K²={stat:.4f}, p={_fmt_p(p)} < {ALPHA}); "
            f"the test detects skew and/or excess kurtosis. Consider a "
            f"non-parametric alternative or a transformation."
        )
    return {"statistic": stat, "p": p, "n": n, "interpretation": interpretation}


# ── Equality of variance ───────────────────────────────────────────────


def _prepare_groups(groups: dict[str, list[float]]) -> list[np.ndarray]:
    if not isinstance(groups, dict):
        raise ValueError("groups must be a dict of label -> list[float]")
    if len(groups) < 2:
        raise ValueError("at least 2 groups are required")
    arrays: list[np.ndarray] = []
    for label, vals in groups.items():
        arr = _to_array(vals)
        if arr.size < 2:
            raise ValueError(
                f"group {label!r} has fewer than 2 non-missing values"
            )
        arrays.append(arr)
    return arrays


def levene(
    groups: dict[str, list[float]], center: str = "median"
) -> dict[str, Any]:
    """Levene's test for equal variances.

    Defaults to ``center='median'`` (the Brown-Forsythe variant), which is
    robust against non-normal data and is the recommended default for
    most clinical-research contexts.
    """
    if center not in {"mean", "median", "trimmed"}:
        raise ValueError("center must be 'mean', 'median', or 'trimmed'")
    arrays = _prepare_groups(groups)
    stat, p = stats.levene(*arrays, center=center)
    stat = float(stat)
    p = float(p)
    n_total = int(sum(a.size for a in arrays))
    if p > ALPHA:
        interpretation = (
            f"Group variances are consistent with equality "
            f"(Levene W={stat:.4f}, p={_fmt_p(p)} > {ALPHA}); "
            f"the equal-variance assumption holds — use the pooled t-test or "
            f"standard one-way ANOVA."
        )
    else:
        interpretation = (
            f"Group variances differ significantly "
            f"(Levene W={stat:.4f}, p={_fmt_p(p)} < {ALPHA}); "
            f"use Welch's t-test or Welch's ANOVA instead of the pooled "
            f"variants, or switch to a non-parametric test."
        )
    return {
        "statistic": stat,
        "p": p,
        "n": n_total,
        "k": len(arrays),
        "center": center,
        "interpretation": interpretation,
    }


def bartlett(groups: dict[str, list[float]]) -> dict[str, Any]:
    """Bartlett's test for equal variances.

    More powerful than Levene when groups are normal, but very sensitive
    to non-normality — the interpretation calls this out.
    """
    arrays = _prepare_groups(groups)
    stat, p = stats.bartlett(*arrays)
    stat = float(stat)
    p = float(p)
    n_total = int(sum(a.size for a in arrays))
    if p > ALPHA:
        interpretation = (
            f"Group variances are consistent with equality "
            f"(Bartlett χ²={stat:.4f}, p={_fmt_p(p)} > {ALPHA}); "
            f"verify normality first — Bartlett is sensitive to departures "
            f"from normal."
        )
    else:
        interpretation = (
            f"Group variances differ significantly "
            f"(Bartlett χ²={stat:.4f}, p={_fmt_p(p)} < {ALPHA}); "
            f"this may be a true variance difference or a normality "
            f"violation — confirm with Levene (Brown-Forsythe) before "
            f"switching to Welch's correction."
        )
    return {
        "statistic": stat,
        "p": p,
        "n": n_total,
        "k": len(arrays),
        "interpretation": interpretation,
    }


# ── Visual diagnostics (PNG bytes) ─────────────────────────────────────


def qq_plot_png(
    values: list[float] | np.ndarray, title: str | None = None
) -> bytes:
    """Render a Q-Q plot against the standard normal and return PNG bytes."""
    from .charts._base import fig_context, fig_to_png_bytes

    arr = _to_array(values)
    if arr.size < 3:
        raise ValueError("Q-Q plot requires at least 3 non-missing values")
    with fig_context() as fig:
        ax = fig.add_subplot(1, 1, 1)
        stats.probplot(arr, dist="norm", plot=ax)
        lines = ax.get_lines()
        if len(lines) >= 2:
            lines[0].set_markerfacecolor("#3b82f6")
            lines[0].set_markeredgecolor("#3b82f6")
            lines[1].set_color("#ef4444")
        ax.set_xlabel("Theoretical quantiles (normal)")
        ax.set_ylabel("Sample quantiles")
        ax.set_title(title or "Normal Q-Q plot")
        return fig_to_png_bytes(fig)


def histogram_normal_overlay_png(
    values: list[float] | np.ndarray, title: str | None = None
) -> bytes:
    """Histogram of ``values`` with a fitted-normal PDF overlay; PNG bytes."""
    from .charts._base import fig_context, fig_to_png_bytes

    arr = _to_array(values)
    if arr.size < 3:
        raise ValueError("Histogram requires at least 3 non-missing values")
    mu = float(arr.mean())
    sd = float(arr.std(ddof=1))
    with fig_context() as fig:
        ax = fig.add_subplot(1, 1, 1)
        # Histogram normalised to density so the overlay is comparable.
        ax.hist(
            arr,
            bins="auto",
            density=True,
            color="#3b82f6",
            edgecolor="white",
            alpha=0.85,
        )
        if np.isfinite(sd) and sd > 0:
            x_lo, x_hi = arr.min(), arr.max()
            pad = (x_hi - x_lo) * 0.1 if x_hi > x_lo else 1.0
            xs = np.linspace(x_lo - pad, x_hi + pad, 200)
            ys = stats.norm.pdf(xs, loc=mu, scale=sd)
            ax.plot(xs, ys, color="#ef4444", linewidth=2.0, label="Fitted normal")
            ax.legend(loc="best", fontsize=9)
        ax.set_xlabel("Value")
        ax.set_ylabel("Density")
        ax.set_title(title or "Histogram with fitted-normal overlay")
        return fig_to_png_bytes(fig)
