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
    if chart is not None:
        result = replace(result, chart=chart)
    return result


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
}


TestResult.__test__ = False  # type: ignore[attr-defined]
