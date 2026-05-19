from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from research_api.services.stats.charts import select_and_render
from research_api.services.stats.registry import CATALOGUE

_COL_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class TestResult:
    test_key: str
    statistic: float
    p_value: float
    effect_size: float | None
    ci_low: float | None
    ci_high: float | None
    n: int
    df: float | None
    extras: dict[str, Any] = field(default_factory=dict)
    chart: dict[str, Any] | None = None


def _check_column_name(name: str) -> None:
    if not isinstance(name, str) or not _COL_NAME_RE.match(name):
        raise ValueError(f"invalid column name {name!r}: must match [A-Za-z_][A-Za-z0-9_]*")


def _require_columns(df: pd.DataFrame, names: list[str]) -> None:
    for n in names:
        if n not in df.columns:
            raise ValueError(f"column {n!r} not found in dataframe")


def _drop_nan(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    return df.dropna(subset=cols).reset_index(drop=True)


def _two_groups(df: pd.DataFrame, outcome: str, groups: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    levels = sorted(df[groups].dropna().unique().tolist(), key=str)
    if len(levels) != 2:
        raise ValueError(f"expected exactly 2 groups in {groups!r}, found {len(levels)}")
    a = df.loc[df[groups] == levels[0], outcome].to_numpy(dtype=float)
    b = df.loc[df[groups] == levels[1], outcome].to_numpy(dtype=float)
    return a, b, [str(levels[0]), str(levels[1])]


def run(
    *,
    test_key: str,
    df: pd.DataFrame,
    variables: dict[str, Any],
) -> TestResult:
    if test_key not in CATALOGUE:
        raise ValueError(f"unknown test_key: {test_key}")
    if not isinstance(variables, dict):
        raise ValueError("variables must be a dict")

    for v in _iter_column_refs(variables):
        _check_column_name(v)

    handler = _DISPATCH[test_key]
    result = handler(df, variables)
    chart = select_and_render(test_key=test_key, df=df, variables=variables)
    # Phase 13 — OLS diagnostic panels merged into chart for OLS-family tests.
    if test_key in {"linear_regression", "multiple_linear"}:
        panels = _ols_diagnostic_panels(df, variables)
        if panels is not None:
            chart = chart or {}
            chart = {**chart, "panels": panels}
    # Phase 13 (MP13) — Charts that need the result's extras dict.
    if chart is None:
        chart = _post_result_chart(test_key, df, variables, result)
    if chart is not None:
        result = replace(result, chart=chart)
    return result


def _post_result_chart(
    test_key: str,
    df: pd.DataFrame,
    variables: dict[str, Any],
    result: "TestResult",
) -> dict[str, Any] | None:
    """Build a chart that depends on `result.extras` (bootstrap, permutation,
    TOST, mixed-effects, GLM, GEE). Returns None on any failure."""
    import logging

    log = logging.getLogger(__name__)
    try:
        if test_key == "bootstrap_mean_diff":
            from research_api.services.stats.charts.bootstrap_dist import (
                render_bootstrap_distribution,
            )

            dist = result.extras.get("bootstrap_distribution") or []
            if not dist:
                return None
            return render_bootstrap_distribution(
                distribution=dist,
                observed=float(result.statistic),
                ci_low=float(result.ci_low) if result.ci_low is not None else float("nan"),
                ci_high=float(result.ci_high) if result.ci_high is not None else float("nan"),
                title="Bootstrap mean difference",
            )
        if test_key == "permutation_test":
            from research_api.services.stats.charts.permutation_dist import (
                render_permutation_distribution,
            )

            dist = result.extras.get("null_distribution") or []
            if not dist:
                return None
            return render_permutation_distribution(
                null_distribution=dist,
                observed=float(result.statistic),
            )
        if test_key in {"tost_equivalence", "tost_noninferiority"}:
            from research_api.services.stats.charts.tost_plot import (
                render_tost_bounds,
            )

            return render_tost_bounds(
                observed_diff=float(result.extras.get("mean_diff", 0.0)),
                low_eq=float(result.extras.get("low_eq", -1.0)),
                upp_eq=float(result.extras.get("upp_eq", 1.0)),
                n_a=int(result.n // 2),
                n_b=int(result.n - result.n // 2),
                title=test_key.replace("_", " ").title(),
            )
        if test_key == "mixed_effects_lm":
            from research_api.services.stats.charts.mixed_effects import (
                render_mixed_effects_caterpillar,
            )

            outcome = variables["outcome"]
            cluster = variables["cluster"]
            predictors = variables["predictors"]
            if isinstance(predictors, str):
                predictors = [predictors]
            return render_mixed_effects_caterpillar(
                df=df,
                outcome=outcome,
                predictors=list(predictors),
                cluster=cluster,
            )
        if test_key in {"glm_poisson", "glm_binomial", "glm_gamma", "gee"}:
            from research_api.services.stats.charts.glm_diagnostics import (
                render_glm_deviance_residuals,
            )

            outcome = variables["outcome"]
            predictors = variables["predictors"]
            if isinstance(predictors, str):
                predictors = [predictors]
            family_map = {
                "glm_poisson": "Poisson",
                "glm_binomial": "Binomial",
                "glm_gamma": "Gamma",
                "gee": "Poisson",  # GEE diagnostic uses a Poisson-shaped chart by convention
            }
            return render_glm_deviance_residuals(
                df=df,
                outcome=outcome,
                predictors=list(predictors),
                family=family_map[test_key],
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("post-result chart failed for %s: %s", test_key, exc)
        return None
    return None


def _ols_diagnostic_panels(
    df: pd.DataFrame, variables: dict[str, Any]
) -> dict[str, str] | None:
    """Render the 4-panel OLS diagnostic PNGs as base64 data URIs.

    Returns None (and logs a warning) on any failure rather than breaking
    the primary analysis result.
    """
    import base64
    import logging

    from .diagnostics import ols_diagnostic_plots

    outcome = variables.get("outcome")
    predictors = variables.get("predictors")
    if not isinstance(outcome, str) or not predictors:
        return None
    if isinstance(predictors, str):
        predictors = [predictors]
    try:
        png_panels = ols_diagnostic_plots(df, outcome, list(predictors))
    except Exception as exc:  # noqa: BLE001
        logging.getLogger(__name__).warning("OLS diagnostics failed: %s", exc)
        return None
    return {
        name: "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
        for name, raw in png_panels.items()
    }


def _iter_column_refs(variables: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for v in variables.values():
        if isinstance(v, str):
            refs.append(v)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, str):
                    refs.append(item)
    return refs


def _independent_t(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    outcome = var.get("outcome")
    groups = var.get("groups")
    if not outcome or not groups:
        raise ValueError("independent_t requires 'outcome' and 'groups'")
    _require_columns(df, [outcome, groups])
    df = _drop_nan(df, [outcome, groups])
    a, b, _ = _two_groups(df, outcome, groups)
    t, p = stats.ttest_ind(a, b, equal_var=True)
    n1, n2 = len(a), len(b)
    pooled = np.sqrt(
        ((a.var(ddof=1) * (n1 - 1)) + (b.var(ddof=1) * (n2 - 1))) / (n1 + n2 - 2)
    )
    d = (a.mean() - b.mean()) / pooled if pooled > 0 else float("nan")
    se = pooled * np.sqrt(1.0 / n1 + 1.0 / n2)
    diff = a.mean() - b.mean()
    df_val = n1 + n2 - 2
    crit = stats.t.ppf(0.975, df_val)
    ci_low = float(diff - crit * se)
    ci_high = float(diff + crit * se)
    return TestResult(
        test_key="independent_t",
        statistic=float(t),
        p_value=float(p),
        effect_size=float(d),
        ci_low=ci_low,
        ci_high=ci_high,
        n=n1 + n2,
        df=float(df_val),
        extras={"mean_diff": float(diff), "n1": n1, "n2": n2},
    )


def _paired_t(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    pre = var.get("pre")
    post = var.get("post")
    if not pre or not post:
        raise ValueError("paired_t requires 'pre' and 'post'")
    _require_columns(df, [pre, post])
    df = _drop_nan(df, [pre, post])
    a = df[pre].to_numpy(dtype=float)
    b = df[post].to_numpy(dtype=float)
    t, p = stats.ttest_rel(a, b)
    diff = b - a
    dz = diff.mean() / diff.std(ddof=1) if diff.std(ddof=1) > 0 else float("nan")
    se = diff.std(ddof=1) / np.sqrt(len(diff))
    crit = stats.t.ppf(0.975, len(diff) - 1)
    ci_low = float(diff.mean() - crit * se)
    ci_high = float(diff.mean() + crit * se)
    return TestResult(
        test_key="paired_t",
        statistic=float(t),
        p_value=float(p),
        effect_size=float(abs(dz)),
        ci_low=ci_low,
        ci_high=ci_high,
        n=len(diff),
        df=float(len(diff) - 1),
        extras={"mean_diff": float(diff.mean())},
    )


def _mann_whitney(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    outcome = var.get("outcome")
    groups = var.get("groups")
    if not outcome or not groups:
        raise ValueError("mann_whitney requires 'outcome' and 'groups'")
    _require_columns(df, [outcome, groups])
    df = _drop_nan(df, [outcome, groups])
    a, b, _ = _two_groups(df, outcome, groups)
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    n1, n2 = len(a), len(b)
    rb = 1.0 - (2.0 * u) / (n1 * n2)
    return TestResult(
        test_key="mann_whitney",
        statistic=float(u),
        p_value=float(p),
        effect_size=float(rb),
        ci_low=None,
        ci_high=None,
        n=n1 + n2,
        df=None,
        extras={"n1": n1, "n2": n2},
    )


def _wilcoxon_signed(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    pre = var.get("pre")
    post = var.get("post")
    if not pre or not post:
        raise ValueError("wilcoxon_signed requires 'pre' and 'post'")
    _require_columns(df, [pre, post])
    df = _drop_nan(df, [pre, post])
    a = df[pre].to_numpy(dtype=float)
    b = df[post].to_numpy(dtype=float)
    w, p = stats.wilcoxon(a, b)
    return TestResult(
        test_key="wilcoxon_signed",
        statistic=float(w),
        p_value=float(p),
        effect_size=None,
        ci_low=None,
        ci_high=None,
        n=len(a),
        df=None,
        extras={},
    )


def _chi_squared(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    outcome = var.get("outcome")
    groups = var.get("groups")
    if not outcome or not groups:
        raise ValueError("chi_squared requires 'outcome' and 'groups'")
    _require_columns(df, [outcome, groups])
    df = _drop_nan(df, [outcome, groups])
    tab = pd.crosstab(df[outcome], df[groups])
    chi2, p, dof, expected = stats.chi2_contingency(tab.values, correction=False)
    n = int(tab.values.sum())
    r, c = tab.shape
    min_dim = min(r - 1, c - 1)
    cramers_v = float(np.sqrt(chi2 / (n * min_dim))) if min_dim > 0 else float("nan")
    return TestResult(
        test_key="chi_squared",
        statistic=float(chi2),
        p_value=float(p),
        effect_size=cramers_v,
        ci_low=None,
        ci_high=None,
        n=n,
        df=float(dof),
        extras={"expected_min": float(expected.min())},
    )


def _fisher_exact(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    outcome = var.get("outcome")
    groups = var.get("groups")
    if not outcome or not groups:
        raise ValueError("fisher_exact requires 'outcome' and 'groups'")
    _require_columns(df, [outcome, groups])
    df = _drop_nan(df, [outcome, groups])
    tab = pd.crosstab(df[outcome], df[groups])
    if tab.shape != (2, 2):
        raise ValueError("fisher_exact requires a 2x2 contingency table")
    odds, p = stats.fisher_exact(tab.values)
    n = int(tab.values.sum())
    return TestResult(
        test_key="fisher_exact",
        statistic=float(odds),
        p_value=float(p),
        effect_size=float(odds),
        ci_low=None,
        ci_high=None,
        n=n,
        df=None,
        extras={"table": tab.values.tolist()},
    )


def _one_way_anova(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    outcome = var.get("outcome")
    groups = var.get("groups")
    if not outcome or not groups:
        raise ValueError("one_way_anova requires 'outcome' and 'groups'")
    _require_columns(df, [outcome, groups])
    df = _drop_nan(df, [outcome, groups])
    levels = sorted(df[groups].dropna().unique().tolist(), key=str)
    arrays = [df.loc[df[groups] == lv, outcome].to_numpy(dtype=float) for lv in levels]
    f, p = stats.f_oneway(*arrays)
    grand_mean = np.concatenate(arrays).mean()
    ss_between = sum(len(a) * (a.mean() - grand_mean) ** 2 for a in arrays)
    ss_total = sum(((np.concatenate(arrays) - grand_mean) ** 2))
    eta_sq = float(ss_between / ss_total) if ss_total > 0 else float("nan")
    n = int(sum(len(a) for a in arrays))
    k = len(arrays)
    return TestResult(
        test_key="one_way_anova",
        statistic=float(f),
        p_value=float(p),
        effect_size=eta_sq,
        ci_low=None,
        ci_high=None,
        n=n,
        df=float(k - 1),
        extras={"df_between": k - 1, "df_within": n - k, "groups": [str(lv) for lv in levels]},
    )


def _kruskal_wallis(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    outcome = var.get("outcome")
    groups = var.get("groups")
    if not outcome or not groups:
        raise ValueError("kruskal_wallis requires 'outcome' and 'groups'")
    _require_columns(df, [outcome, groups])
    df = _drop_nan(df, [outcome, groups])
    levels = sorted(df[groups].dropna().unique().tolist(), key=str)
    arrays = [df.loc[df[groups] == lv, outcome].to_numpy(dtype=float) for lv in levels]
    h, p = stats.kruskal(*arrays)
    n = int(sum(len(a) for a in arrays))
    return TestResult(
        test_key="kruskal_wallis",
        statistic=float(h),
        p_value=float(p),
        effect_size=None,
        ci_low=None,
        ci_high=None,
        n=n,
        df=float(len(arrays) - 1),
        extras={"k": len(arrays)},
    )


def _rm_anova(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    import pingouin as pg

    outcome = var.get("outcome")
    within = var.get("within")
    subject = var.get("subject")
    if not outcome or not within or not subject:
        raise ValueError("rm_anova requires 'outcome', 'within', 'subject'")
    _require_columns(df, [outcome, within, subject])
    df = _drop_nan(df, [outcome, within, subject])
    out = pg.rm_anova(data=df, dv=outcome, within=within, subject=subject, detailed=True)
    row = out.iloc[0]
    return TestResult(
        test_key="rm_anova",
        statistic=float(row["F"]),
        p_value=float(row["p_unc"]),
        effect_size=float(row.get("ng2", row.get("np2", float("nan")))),
        ci_low=None,
        ci_high=None,
        n=int(df[subject].nunique()),
        df=float(row["DF"]),
        extras={"source": str(row["Source"])},
    )


def _pearson(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    x = var.get("x")
    y = var.get("y")
    if not x or not y:
        raise ValueError("pearson requires 'x' and 'y'")
    _require_columns(df, [x, y])
    df = _drop_nan(df, [x, y])
    res = stats.pearsonr(df[x].to_numpy(dtype=float), df[y].to_numpy(dtype=float))
    r = float(res.statistic)
    p = float(res.pvalue)
    n = len(df)
    if n > 3:
        z = np.arctanh(r)
        se = 1.0 / np.sqrt(n - 3)
        z_crit = 1.959963984540054
        lo = float(np.tanh(z - z_crit * se))
        hi = float(np.tanh(z + z_crit * se))
    else:
        lo = hi = None
    return TestResult(
        test_key="pearson",
        statistic=r,
        p_value=p,
        effect_size=r,
        ci_low=lo,
        ci_high=hi,
        n=n,
        df=float(n - 2),
        extras={},
    )


def _spearman(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    x = var.get("x")
    y = var.get("y")
    if not x or not y:
        raise ValueError("spearman requires 'x' and 'y'")
    _require_columns(df, [x, y])
    df = _drop_nan(df, [x, y])
    res = stats.spearmanr(df[x].to_numpy(dtype=float), df[y].to_numpy(dtype=float))
    r = float(res.statistic)
    p = float(res.pvalue)
    n = len(df)
    return TestResult(
        test_key="spearman",
        statistic=r,
        p_value=p,
        effect_size=r,
        ci_low=None,
        ci_high=None,
        n=n,
        df=float(n - 2),
        extras={},
    )


def _ols(df: pd.DataFrame, outcome: str, predictors: list[str], test_key: str) -> TestResult:
    import statsmodels.formula.api as smf

    _check_column_name(outcome)
    for p in predictors:
        _check_column_name(p)
    _require_columns(df, [outcome, *predictors])
    df = _drop_nan(df, [outcome, *predictors])
    formula = f"{outcome} ~ " + " + ".join(predictors)
    model = smf.ols(formula, data=df).fit()
    coefs = {f"coef_{name}": float(model.params[name]) for name in predictors if name in model.params}
    return TestResult(
        test_key=test_key,
        statistic=float(model.fvalue),
        p_value=float(model.f_pvalue),
        effect_size=float(model.rsquared),
        ci_low=None,
        ci_high=None,
        n=int(model.nobs),
        df=float(model.df_model),
        extras={
            "r_squared": float(model.rsquared),
            "adj_r_squared": float(model.rsquared_adj),
            "intercept": float(model.params.get("Intercept", float("nan"))),
            **coefs,
        },
    )


def _linear_regression(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    outcome = var.get("outcome")
    predictors = var.get("predictors")
    if not outcome or not predictors:
        raise ValueError("linear_regression requires 'outcome' and 'predictors'")
    if isinstance(predictors, str):
        predictors = [predictors]
    return _ols(df, outcome, list(predictors), "linear_regression")


def _multiple_linear(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    outcome = var.get("outcome")
    predictors = var.get("predictors")
    if not outcome or not predictors:
        raise ValueError("multiple_linear requires 'outcome' and 'predictors'")
    if isinstance(predictors, str):
        predictors = [predictors]
    return _ols(df, outcome, list(predictors), "multiple_linear")


def _logistic(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    import statsmodels.formula.api as smf

    outcome = var.get("outcome")
    predictors = var.get("predictors")
    if not outcome or not predictors:
        raise ValueError("logistic requires 'outcome' and 'predictors'")
    if isinstance(predictors, str):
        predictors = [predictors]
    _check_column_name(outcome)
    for p in predictors:
        _check_column_name(p)
    _require_columns(df, [outcome, *predictors])
    df = _drop_nan(df, [outcome, *predictors])
    formula = f"{outcome} ~ " + " + ".join(predictors)
    model = smf.logit(formula, data=df).fit(disp=0)
    coefs = {f"coef_{name}": float(model.params[name]) for name in predictors}
    ors = {f"or_{name}": float(np.exp(model.params[name])) for name in predictors}
    pvals = {f"p_{name}": float(model.pvalues[name]) for name in predictors}
    return TestResult(
        test_key="logistic",
        statistic=float(model.llr),
        p_value=float(model.llr_pvalue),
        effect_size=float(model.prsquared),
        ci_low=None,
        ci_high=None,
        n=int(model.nobs),
        df=float(model.df_model),
        extras={
            "pseudo_r2": float(model.prsquared),
            "intercept": float(model.params.get("Intercept", float("nan"))),
            **coefs,
            **ors,
            **pvals,
        },
    )


def _kaplan_meier(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    from lifelines import KaplanMeierFitter
    from lifelines.statistics import logrank_test

    time = var.get("time")
    event = var.get("event")
    groups = var.get("groups")
    if not time or not event:
        raise ValueError("kaplan_meier requires 'time' and 'event'")
    _require_columns(df, [time, event] + ([groups] if groups else []))
    df = _drop_nan(df, [time, event] + ([groups] if groups else []))

    chart_series: list[dict[str, Any]] = []

    if groups is None:
        kmf = KaplanMeierFitter().fit(df[time], df[event])
        sf = kmf.survival_function_
        chart_series.append(
            {
                "label": "all",
                "times": sf.index.tolist(),
                "survival": sf.iloc[:, 0].tolist(),
            }
        )
        n = int(len(df))
        return TestResult(
            test_key="kaplan_meier",
            statistic=float("nan"),
            p_value=float("nan"),
            effect_size=None,
            ci_low=None,
            ci_high=None,
            n=n,
            df=None,
            extras={"groups": ["all"]},
            chart={"type": "kaplan_meier", "series": chart_series},
        )

    levels = sorted(df[groups].dropna().unique().tolist(), key=str)
    if len(levels) != 2:
        for lv in levels:
            sub = df[df[groups] == lv]
            kmf = KaplanMeierFitter().fit(sub[time], sub[event], label=str(lv))
            sf = kmf.survival_function_
            chart_series.append(
                {"label": str(lv), "times": sf.index.tolist(), "survival": sf.iloc[:, 0].tolist()}
            )
        return TestResult(
            test_key="kaplan_meier",
            statistic=float("nan"),
            p_value=float("nan"),
            effect_size=None,
            ci_low=None,
            ci_high=None,
            n=int(len(df)),
            df=float(len(levels) - 1),
            extras={"groups": [str(lv) for lv in levels]},
            chart={"type": "kaplan_meier", "series": chart_series},
        )

    a = df[df[groups] == levels[0]]
    b = df[df[groups] == levels[1]]
    res = logrank_test(
        a[time], b[time], event_observed_A=a[event], event_observed_B=b[event]
    )
    for sub, lv in [(a, levels[0]), (b, levels[1])]:
        kmf = KaplanMeierFitter().fit(sub[time], sub[event], label=str(lv))
        sf = kmf.survival_function_
        chart_series.append(
            {"label": str(lv), "times": sf.index.tolist(), "survival": sf.iloc[:, 0].tolist()}
        )
    return TestResult(
        test_key="kaplan_meier",
        statistic=float(res.test_statistic),
        p_value=float(res.p_value),
        effect_size=None,
        ci_low=None,
        ci_high=None,
        n=int(len(df)),
        df=1.0,
        extras={"groups": [str(levels[0]), str(levels[1])]},
        chart={"type": "kaplan_meier", "series": chart_series},
    )


def _cox_ph(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    from lifelines import CoxPHFitter

    time = var.get("time")
    event = var.get("event")
    covariates = var.get("covariates")
    if not time or not event or not covariates:
        raise ValueError("cox_ph requires 'time', 'event', 'covariates'")
    if isinstance(covariates, str):
        covariates = [covariates]
    _require_columns(df, [time, event, *covariates])
    df = _drop_nan(df, [time, event, *covariates])
    fit_df = df[[time, event, *covariates]]
    cph = CoxPHFitter()
    cph.fit(fit_df, duration_col=time, event_col=event)
    summary = cph.summary
    primary = covariates[0]
    hr_primary = float(np.exp(summary["coef"].loc[primary]))
    p_primary = float(summary["p"].loc[primary])
    extras: dict[str, Any] = {}
    for c in covariates:
        extras[f"coef_{c}"] = float(summary["coef"].loc[c])
        extras[f"hr_{c}"] = float(np.exp(summary["coef"].loc[c]))
        extras[f"p_{c}"] = float(summary["p"].loc[c])
    return TestResult(
        test_key="cox_ph",
        statistic=float(summary["z"].loc[primary]),
        p_value=p_primary,
        effect_size=hr_primary,
        ci_low=float(np.exp(summary["coef lower 95%"].loc[primary])),
        ci_high=float(np.exp(summary["coef upper 95%"].loc[primary])),
        n=int(cph._n_examples),
        df=float(len(covariates)),
        extras=extras,
    )


def _icc(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    import pingouin as pg

    subject = var.get("subject")
    rater = var.get("rater")
    rating = var.get("rating")
    if not subject or not rater or not rating:
        raise ValueError("icc requires 'subject', 'rater', 'rating'")
    _require_columns(df, [subject, rater, rating])
    df = _drop_nan(df, [subject, rater, rating])
    out = pg.intraclass_corr(data=df, targets=subject, raters=rater, ratings=rating)
    row = out.iloc[0]
    ci_key = "CI95%" if "CI95%" in out.columns else "CI95"
    ci_pair = row[ci_key]
    return TestResult(
        test_key="icc",
        statistic=float(row["ICC"]),
        p_value=float(row["pval"]),
        effect_size=float(row["ICC"]),
        ci_low=float(ci_pair[0]),
        ci_high=float(ci_pair[1]),
        n=int(df[subject].nunique()),
        df=float(row["df1"]),
        extras={"type": str(row["Type"]), "F": float(row["F"])},
    )


def _cohen_kappa(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    a_col = var.get("rater_a")
    b_col = var.get("rater_b")
    if not a_col or not b_col:
        raise ValueError("cohen_kappa requires 'rater_a' and 'rater_b'")
    _require_columns(df, [a_col, b_col])
    df = _drop_nan(df, [a_col, b_col])
    a = df[a_col].tolist()
    b = df[b_col].tolist()
    classes = sorted(set(a) | set(b), key=str)
    n = len(a)
    agree = sum(1 for x, y in zip(a, b) if x == y)
    po = agree / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in classes)
    kappa = (po - pe) / (1 - pe) if (1 - pe) > 0 else float("nan")
    return TestResult(
        test_key="cohen_kappa",
        statistic=float(kappa),
        p_value=float("nan"),
        effect_size=float(kappa),
        ci_low=None,
        ci_high=None,
        n=n,
        df=None,
        extras={"po": float(po), "pe": float(pe), "classes": [str(c) for c in classes]},
    )


def _mixed_effects_lm(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    """Phase 13 (MP13) — Linear mixed-effects model with a random intercept.

    Requires ``outcome``, ``predictors`` (list or single str), and ``cluster``
    (grouping variable, e.g. patient_id). The random-effects structure is a
    random intercept per cluster.
    """
    import statsmodels.formula.api as smf

    outcome = var.get("outcome")
    predictors = var.get("predictors")
    cluster = var.get("cluster")
    if not outcome or not predictors or not cluster:
        raise ValueError(
            "mixed_effects_lm requires 'outcome', 'predictors', and 'cluster'"
        )
    if isinstance(predictors, str):
        predictors = [predictors]
    _check_column_name(outcome)
    _check_column_name(cluster)
    for p in predictors:
        _check_column_name(p)
    _require_columns(df, [outcome, cluster, *predictors])
    df = _drop_nan(df, [outcome, cluster, *predictors])
    formula = f"{outcome} ~ " + " + ".join(predictors)
    model = smf.mixedlm(formula, data=df, groups=df[cluster])
    fit = model.fit(method="lbfgs")
    fe_coefs = {f"coef_{name}": float(fit.fe_params.get(name, float("nan"))) for name in predictors}
    fe_pvals = {f"p_{name}": float(fit.pvalues.get(name, float("nan"))) for name in predictors}
    re_var = float(fit.cov_re.iloc[0, 0]) if hasattr(fit.cov_re, "iloc") else float("nan")
    return TestResult(
        test_key="mixed_effects_lm",
        statistic=float(fe_coefs.get(f"coef_{predictors[0]}", float("nan"))),
        p_value=float(fe_pvals.get(f"p_{predictors[0]}", float("nan"))),
        effect_size=None,
        ci_low=None,
        ci_high=None,
        n=int(fit.nobs),
        df=float(len(predictors)),
        extras={
            "intercept": float(fit.fe_params.get("Intercept", float("nan"))),
            "n_clusters": int(df[cluster].nunique()),
            "random_intercept_var": re_var,
            **fe_coefs,
            **fe_pvals,
        },
    )


def _glm(
    df: pd.DataFrame,
    var: dict[str, Any],
    family_name: str,
    test_key: str,
) -> TestResult:
    """Generic statsmodels GLM dispatch — Poisson / Binomial / Gamma."""
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    outcome = var.get("outcome")
    predictors = var.get("predictors")
    if not outcome or not predictors:
        raise ValueError(f"{test_key} requires 'outcome' and 'predictors'")
    if isinstance(predictors, str):
        predictors = [predictors]
    _check_column_name(outcome)
    for p in predictors:
        _check_column_name(p)
    _require_columns(df, [outcome, *predictors])
    df = _drop_nan(df, [outcome, *predictors])

    family_map = {
        "Poisson": sm.families.Poisson(),
        "Binomial": sm.families.Binomial(),
        "Gamma": sm.families.Gamma(link=sm.families.links.Log()),
    }
    family = family_map[family_name]

    formula = f"{outcome} ~ " + " + ".join(predictors)
    model = smf.glm(formula, data=df, family=family).fit()
    coefs = {f"coef_{name}": float(model.params[name]) for name in predictors}
    pvals = {f"p_{name}": float(model.pvalues[name]) for name in predictors}
    deviance = float(model.deviance)
    return TestResult(
        test_key=test_key,
        statistic=float(model.params.get(predictors[0], float("nan"))),
        p_value=float(model.pvalues.get(predictors[0], float("nan"))),
        effect_size=None,
        ci_low=None,
        ci_high=None,
        n=int(model.nobs),
        df=float(model.df_model),
        extras={
            "family": family_name,
            "intercept": float(model.params.get("Intercept", float("nan"))),
            "deviance": deviance,
            "df_resid": float(model.df_resid),
            **coefs,
            **pvals,
        },
    )


def _glm_poisson(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    return _glm(df, var, "Poisson", "glm_poisson")


def _glm_binomial(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    return _glm(df, var, "Binomial", "glm_binomial")


def _glm_gamma(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    return _glm(df, var, "Gamma", "glm_gamma")


def _gee(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    """GEE with an exchangeable working correlation."""
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    outcome = var.get("outcome")
    predictors = var.get("predictors")
    cluster = var.get("cluster")
    if not outcome or not predictors or not cluster:
        raise ValueError("gee requires 'outcome', 'predictors', 'cluster'")
    if isinstance(predictors, str):
        predictors = [predictors]
    _check_column_name(outcome)
    _check_column_name(cluster)
    for p in predictors:
        _check_column_name(p)
    _require_columns(df, [outcome, cluster, *predictors])
    df = _drop_nan(df, [outcome, cluster, *predictors])
    formula = f"{outcome} ~ " + " + ".join(predictors)
    model = smf.gee(
        formula, groups=cluster, data=df, cov_struct=sm.cov_struct.Exchangeable()
    ).fit()
    coefs = {f"coef_{name}": float(model.params[name]) for name in predictors}
    pvals = {f"p_{name}": float(model.pvalues[name]) for name in predictors}
    return TestResult(
        test_key="gee",
        statistic=float(model.params.get(predictors[0], float("nan"))),
        p_value=float(model.pvalues.get(predictors[0], float("nan"))),
        effect_size=None,
        ci_low=None,
        ci_high=None,
        n=int(model.nobs),
        df=float(len(predictors)),
        extras={
            "cov_struct": "exchangeable",
            "n_clusters": int(df[cluster].nunique()),
            "intercept": float(model.params.get("Intercept", float("nan"))),
            **coefs,
            **pvals,
        },
    )


def _bootstrap_mean_diff(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    """Distribution-free 95% CI on (mean_b - mean_a) via 9,999 bootstrap resamples."""
    outcome = var.get("outcome")
    groups = var.get("groups")
    if not outcome or not groups:
        raise ValueError("bootstrap_mean_diff requires 'outcome' and 'groups'")
    _require_columns(df, [outcome, groups])
    df = _drop_nan(df, [outcome, groups])
    a, b, labels = _two_groups(df, outcome, groups)
    diff_obs = float(b.mean() - a.mean())

    def _stat(x: np.ndarray, y: np.ndarray, axis: int = -1) -> np.ndarray:
        return np.mean(y, axis=axis) - np.mean(x, axis=axis)

    rng = np.random.default_rng(0xBEEF)
    res = stats.bootstrap(
        (a, b),
        statistic=_stat,
        vectorized=True,
        paired=False,
        n_resamples=9999,
        method="basic",
        confidence_level=0.95,
        random_state=rng,
    )
    ci_low = float(res.confidence_interval.low)
    ci_high = float(res.confidence_interval.high)
    return TestResult(
        test_key="bootstrap_mean_diff",
        statistic=diff_obs,
        p_value=float("nan"),
        effect_size=diff_obs,
        ci_low=ci_low,
        ci_high=ci_high,
        n=int(len(a) + len(b)),
        df=None,
        extras={
            "labels": labels,
            "n_resamples": 9999,
            "mean_a": float(a.mean()),
            "mean_b": float(b.mean()),
            "bootstrap_distribution": res.bootstrap_distribution.tolist(),
        },
    )


def _permutation_test(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    """Permutation test for difference in means."""
    outcome = var.get("outcome")
    groups = var.get("groups")
    if not outcome or not groups:
        raise ValueError("permutation_test requires 'outcome' and 'groups'")
    _require_columns(df, [outcome, groups])
    df = _drop_nan(df, [outcome, groups])
    a, b, labels = _two_groups(df, outcome, groups)

    def _stat(x: np.ndarray, y: np.ndarray, axis: int = -1) -> np.ndarray:
        return np.mean(x, axis=axis) - np.mean(y, axis=axis)

    rng = np.random.default_rng(0xCAFE)
    res = stats.permutation_test(
        (a, b),
        statistic=_stat,
        permutation_type="independent",
        n_resamples=9999,
        alternative="two-sided",
        random_state=rng,
        vectorized=True,
    )
    return TestResult(
        test_key="permutation_test",
        statistic=float(res.statistic),
        p_value=float(res.pvalue),
        effect_size=float(res.statistic),
        ci_low=None,
        ci_high=None,
        n=int(len(a) + len(b)),
        df=None,
        extras={
            "labels": labels,
            "n_resamples": 9999,
            "null_distribution": res.null_distribution.tolist(),
        },
    )


def _tost(
    df: pd.DataFrame,
    var: dict[str, Any],
    test_key: str,
) -> TestResult:
    """Two One-Sided Tests for equivalence (or non-inferiority).

    Requires ``low_eq`` and ``upp_eq`` margins. For non-inferiority the
    caller passes ``low_eq = -margin`` and ``upp_eq = +inf`` (or a very
    large number), but we accept whatever margins the form supplied.
    """
    from statsmodels.stats.weightstats import ttost_ind

    outcome = var.get("outcome")
    groups = var.get("groups")
    low_eq = var.get("low_eq")
    upp_eq = var.get("upp_eq")
    if not outcome or not groups:
        raise ValueError(f"{test_key} requires 'outcome' and 'groups'")
    if low_eq is None or upp_eq is None:
        raise ValueError(f"{test_key} requires 'low_eq' and 'upp_eq' margins")
    _require_columns(df, [outcome, groups])
    df = _drop_nan(df, [outcome, groups])
    a, b, labels = _two_groups(df, outcome, groups)
    p_value, t_lower, t_upper = ttost_ind(
        a, b, low=float(low_eq), upp=float(upp_eq), usevar="unequal"
    )
    return TestResult(
        test_key=test_key,
        statistic=float(max(t_lower[0], t_upper[0])),
        p_value=float(p_value),
        effect_size=float(a.mean() - b.mean()),
        ci_low=None,
        ci_high=None,
        n=int(len(a) + len(b)),
        df=None,
        extras={
            "labels": labels,
            "low_eq": float(low_eq),
            "upp_eq": float(upp_eq),
            "mean_diff": float(a.mean() - b.mean()),
            "t_lower": float(t_lower[0]),
            "p_lower": float(t_lower[1]),
            "t_upper": float(t_upper[0]),
            "p_upper": float(t_upper[1]),
        },
    )


def _tost_equivalence(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    return _tost(df, var, "tost_equivalence")


def _tost_noninferiority(df: pd.DataFrame, var: dict[str, Any]) -> TestResult:
    return _tost(df, var, "tost_noninferiority")


_DISPATCH = {
    "independent_t": _independent_t,
    "paired_t": _paired_t,
    "mann_whitney": _mann_whitney,
    "wilcoxon_signed": _wilcoxon_signed,
    "chi_squared": _chi_squared,
    "fisher_exact": _fisher_exact,
    "one_way_anova": _one_way_anova,
    "kruskal_wallis": _kruskal_wallis,
    "rm_anova": _rm_anova,
    "pearson": _pearson,
    "spearman": _spearman,
    "linear_regression": _linear_regression,
    "multiple_linear": _multiple_linear,
    "logistic": _logistic,
    "kaplan_meier": _kaplan_meier,
    "cox_ph": _cox_ph,
    "icc": _icc,
    "cohen_kappa": _cohen_kappa,
    # Phase 13 (MP13)
    "mixed_effects_lm": _mixed_effects_lm,
    "glm_poisson": _glm_poisson,
    "glm_binomial": _glm_binomial,
    "glm_gamma": _glm_gamma,
    "gee": _gee,
    "bootstrap_mean_diff": _bootstrap_mean_diff,
    "permutation_test": _permutation_test,
    "tost_equivalence": _tost_equivalence,
    "tost_noninferiority": _tost_noninferiority,
}


TestResult.__test__ = False  # type: ignore[attr-defined]
