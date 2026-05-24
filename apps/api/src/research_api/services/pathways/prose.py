"""F3 — Manuscript-ready prose generators for each pathway result.

Each ``prose_<pathway>(result, display_labels=None)`` returns a dict with
``methods`` (string) and ``results`` (string), each 1-2 short paragraphs
in clinical-research-paper style.

The result blobs come straight from the orchestrators in this package.
"""
from __future__ import annotations

import math
from typing import Any


def _fmt_p(p: float | None) -> str:
    if p is None or not isinstance(p, (int, float)) or (isinstance(p, float) and math.isnan(p)):
        return "p=NA"
    if p < 0.001:
        return "p<0.001"
    return f"p={p:.3f}"


def _fmt_num(v: Any, digits: int = 2) -> str:
    if v is None:
        return "NA"
    try:
        f = float(v)
    except Exception:
        return str(v)
    if math.isnan(f) or math.isinf(f):
        return "NA"
    return f"{f:.{digits}f}"


def _fmt_ci(low: Any, high: Any, digits: int = 2) -> str:
    return f"{_fmt_num(low, digits)} to {_fmt_num(high, digits)}"


def _label(name: str, labels: dict[str, str] | None) -> str:
    if not name:
        return name
    if labels and name in labels and labels[name]:
        return labels[name]
    return name


TEST_NAMES = {
    "student_t": "Student's t-test",
    "welch_t": "Welch's t-test",
    "mann_whitney": "Mann-Whitney U test",
    "chi_squared": "chi-square test of independence",
    "fisher_exact": "Fisher's exact test",
}


def prose_two_group(
    result: dict[str, Any],
    *,
    display_labels: dict[str, str] | None = None,
) -> dict[str, str]:
    outcome = _label(result["outcome"], display_labels)
    group = _label(result["group"], display_labels)
    level_a = str(result["level_a"])
    level_b = str(result["level_b"])
    test_used = TEST_NAMES.get(result["test_used"], result["test_used"])
    p_str = _fmt_p(result["p_value"])

    if result["outcome_type"] == "numeric":
        desc_a = result["descriptives"][level_a]
        desc_b = result["descriptives"][level_b]
        n_a, n_b = result["n_a"], result["n_b"]
        assumptions = result["assumptions"]
        if result["test_used"] in {"student_t", "welch_t"}:
            methods = (
                f"Methods: {outcome} was compared between {group}={level_a} "
                f"(n={n_a}) and {group}={level_b} (n={n_b}). "
                f"Normality was assessed by Shapiro-Wilk "
                f"(p={_fmt_num(assumptions['shapiro_p_a'], 3)} and "
                f"p={_fmt_num(assumptions['shapiro_p_b'], 3)}), and equality "
                f"of variances by Levene's test "
                f"(p={_fmt_num(assumptions['levene_p'], 3)}). "
                f"Given the data met parametric assumptions, "
                f"a {test_used} was used. "
                f"Effect size is reported as Cohen's d; the 95% "
                f"confidence interval is for the mean difference."
            )
            mean_diff = _fmt_num(result["mean_diff"])
            ci = _fmt_ci(result["ci_low"], result["ci_high"])
            d = _fmt_num(result["effect_size"])
            results = (
                f"Results: Mean {outcome} was "
                f"{_fmt_num(desc_a['mean'])} +/- {_fmt_num(desc_a['sd'])} in "
                f"{level_a} versus "
                f"{_fmt_num(desc_b['mean'])} +/- {_fmt_num(desc_b['sd'])} in "
                f"{level_b} (mean difference {mean_diff}, 95% CI {ci}; "
                f"Cohen's d={d}; {p_str})."
            )
        else:
            methods = (
                f"Methods: {outcome} was compared between {group}={level_a} "
                f"(n={n_a}) and {group}={level_b} (n={n_b}). "
                f"Because Shapiro-Wilk indicated departure from normality "
                f"(p={_fmt_num(assumptions['shapiro_p_a'], 3)} or "
                f"p={_fmt_num(assumptions['shapiro_p_b'], 3)} <= 0.05), a "
                f"Mann-Whitney U test was used. Continuous data are "
                f"summarised as median [IQR]."
            )
            results = (
                f"Results: Median {outcome} was "
                f"{_fmt_num(desc_a['median'])} [{_fmt_num(desc_a['q1'])}-"
                f"{_fmt_num(desc_a['q3'])}] in {level_a} versus "
                f"{_fmt_num(desc_b['median'])} [{_fmt_num(desc_b['q1'])}-"
                f"{_fmt_num(desc_b['q3'])}] in {level_b} (U={_fmt_num(result['statistic'], 1)}; "
                f"rank-biserial r={_fmt_num(result['effect_size'])}; {p_str})."
            )
        return {"methods": methods, "results": results}

    # Categorical outcome.
    n_a, n_b = result["n_a"], result["n_b"]
    table = result["table"]
    levels = result["outcome_levels"]
    methods_extra = (
        " Continuity correction was not applied. "
        if result["test_used"] == "chi_squared"
        else " Fisher's exact test was used because the smallest expected "
        "cell count was <5. "
    )
    methods = (
        f"Methods: The distribution of {outcome} was compared across "
        f"{group}={level_a} (n={n_a}) and {group}={level_b} (n={n_b}) using a "
        f"{test_used}.{methods_extra}"
        f"Effect size is reported as "
        f"{'Cramer''s V' if result['test_used'] == 'chi_squared' else 'the unadjusted odds ratio'} "
        f"with the 95% confidence interval."
    )

    def _pct(num: int, denom: int) -> str:
        if denom == 0:
            return "0/0 (NA)"
        return f"{num}/{denom} ({100.0 * num / denom:.1f}%)"

    cells: list[str] = []
    for i, lv in enumerate(levels):
        a_n = int(table[i][0])
        b_n = int(table[i][1])
        cells.append(
            f"{lv}: {_pct(a_n, n_a)} in {level_a} versus {_pct(b_n, n_b)} in {level_b}"
        )
    parts = "; ".join(cells)
    if result["test_used"] == "fisher_exact":
        eff = f"odds ratio {_fmt_num(result.get('odds_ratio'))} (95% CI {_fmt_ci(result.get('ci_low'), result.get('ci_high'))})"
    elif result["test_used"] == "chi_squared" and "odds_ratio" in result:
        eff = (
            f"chi2={_fmt_num(result['statistic'])}, df={int(result['df'])}, "
            f"odds ratio {_fmt_num(result.get('odds_ratio'))} "
            f"(95% CI {_fmt_ci(result.get('ci_low'), result.get('ci_high'))})"
        )
    else:
        eff = (
            f"chi2={_fmt_num(result['statistic'])}, df={int(result['df'])}, "
            f"Cramer's V={_fmt_num(result['effect_size'])}"
        )
    results = f"Results: {parts}. {eff}; {p_str}."
    return {"methods": methods, "results": results}


def prose_risk_factors(
    result: dict[str, Any],
    *,
    display_labels: dict[str, str] | None = None,
) -> dict[str, str]:
    outcome = _label(result["outcome"], display_labels)
    is_logistic = result["model"] == "logistic"
    model_name = "multivariable logistic regression" if is_logistic else "multivariable linear regression"
    units = "adjusted odds ratios (aOR)" if is_logistic else "regression coefficients (beta)"
    omnibus = result.get("omnibus") or {}
    confounders = result.get("confounders") or []
    pred_str = ", ".join(_label(p, display_labels) for p in result["predictors"])
    conf_str = (
        f" Adjustment variables included {', '.join(_label(c, display_labels) for c in confounders)}."
        if confounders
        else ""
    )

    methods = (
        f"Methods: Predictors of {outcome} were assessed by univariable "
        f"regression for each candidate variable ({pred_str}), followed by a "
        f"{model_name} entering all candidate predictors simultaneously."
        f"{conf_str} Estimates are reported as {units} with 95% "
        f"confidence intervals. Multicollinearity was checked via the "
        f"variance inflation factor."
    )

    rows: list[str] = []
    for row in result["multivariable"]:
        if row.get("estimate") is None:
            continue
        eff = _fmt_num(row["estimate"])
        ci = _fmt_ci(row["ci_low"], row["ci_high"])
        lbl = row["estimate_label"]
        rows.append(
            f"{row['term']}: {lbl}={eff} (95% CI {ci}; {_fmt_p(row['p_value'])})"
        )
    body = "; ".join(rows) if rows else "no estimable coefficients"

    if is_logistic and "auc" in omnibus:
        fit = (
            f" The model explained {_fmt_num(omnibus.get('pseudo_r2'), 3)} of the "
            f"deviance (McFadden R2) with discrimination AUC "
            f"{_fmt_num(omnibus.get('auc'), 3)}; Hosmer-Lemeshow "
            f"{_fmt_p(omnibus.get('hosmer_lemeshow_p'))}."
        )
    elif not is_logistic and "r_squared" in omnibus:
        fit = (
            f" The model explained {_fmt_num(omnibus.get('r_squared'), 3)} of "
            f"the variance in {outcome} (adjusted R2="
            f"{_fmt_num(omnibus.get('adj_r_squared'), 3)}; "
            f"F={_fmt_num(omnibus.get('f_statistic'))}; "
            f"{_fmt_p(omnibus.get('f_p_value'))})."
        )
    else:
        fit = ""
    vif_warn = ""
    if omnibus.get("multicollinearity_warning"):
        vif_warn = (
            f" Maximum VIF was {_fmt_num(omnibus.get('max_vif'))}, "
            f"indicating possible multicollinearity."
        )
    results = (
        f"Results: Based on {result['n']} complete-case observations, the "
        f"multivariable model yielded {body}.{fit}{vif_warn}"
    )
    return {"methods": methods, "results": results}


def prose_survival(
    result: dict[str, Any],
    *,
    display_labels: dict[str, str] | None = None,
) -> dict[str, str]:
    time = _label(result["time"], display_labels)
    event = _label(result["event"], display_labels)
    strata = _label(result["strata"], display_labels) if result.get("strata") else None
    predictors = result.get("predictors") or []
    overall = result["overall"]
    median = overall.get("median_survival")
    median_str = "not reached" if median is None or median != median or (isinstance(median, float) and math.isinf(median)) else _fmt_num(median)

    extra_methods = ""
    if strata:
        extra_methods += (
            f" Survival was compared between {strata} levels using the log-rank test."
        )
    if predictors:
        extra_methods += (
            f" A Cox proportional-hazards model was fitted with the "
            f"following covariates: {', '.join(_label(p, display_labels) for p in predictors)}. "
            f"The proportional-hazards assumption was tested via Schoenfeld residuals."
        )
    methods = (
        f"Methods: Time to {event} was analysed using Kaplan-Meier survival "
        f"estimates with {time} as the time scale.{extra_methods}"
    )

    res = (
        f"Results: Across {result['n']} subjects with "
        f"{result['n_events']} events, the median survival was {median_str}."
    )
    if "logrank" in result and "p_value" in result["logrank"]:
        lr = result["logrank"]
        res += (
            f" The log-rank test comparing strata of {strata} yielded "
            f"chi2={_fmt_num(lr['test_statistic'])}, df={int(lr['df'])} "
            f"({_fmt_p(lr['p_value'])})."
        )
    cox = result.get("cox") or {}
    if cox.get("terms"):
        bits: list[str] = []
        for row in cox["terms"]:
            bits.append(
                f"{row['term']}: HR={_fmt_num(row['estimate'])} (95% CI "
                f"{_fmt_ci(row['ci_low'], row['ci_high'])}; "
                f"{_fmt_p(row['p_value'])})"
            )
        res += (
            f" In the Cox model (c-index={_fmt_num(cox.get('concordance'), 3)}), "
            f"the adjusted hazard ratios were: {'; '.join(bits)}."
        )
        ph = cox.get("ph_assumption") or {}
        if "global_p" in ph:
            res += (
                f" Test of proportional hazards: "
                f"{_fmt_p(ph.get('global_p'))}"
                f"{' (assumption violated).' if ph.get('violated') else '.'}"
            )
    return {"methods": methods, "results": res}


def prose_diagnostic(
    result: dict[str, Any],
    *,
    display_labels: dict[str, str] | None = None,
) -> dict[str, str]:
    test = _label(result["test"], display_labels)
    reference = _label(result["reference"], display_labels)

    if result.get("test_type") == "continuous":
        methods = (
            f"Methods: Diagnostic accuracy of {test} for {reference} was "
            f"assessed by receiver operating characteristic (ROC) analysis. "
            f"The optimal classification threshold was chosen by Youden's J "
            f"statistic. Sensitivity, specificity, predictive values and "
            f"likelihood ratios were calculated at that threshold. The area "
            f"under the curve (AUC) is reported with a 95% confidence "
            f"interval (Hanley-McNeil)."
        )
        m = result["at_optimal"]
        res = (
            f"Results: AUC was {_fmt_num(result['auc'], 3)} "
            f"(95% CI {_fmt_num(result['auc_ci_low'], 3)} to "
            f"{_fmt_num(result['auc_ci_high'], 3)}). At the optimal "
            f"threshold of {_fmt_num(result['optimal_threshold'])}, "
            f"sensitivity was {_fmt_num(m['sensitivity'], 3)} "
            f"(95% CI {_fmt_num(m['sensitivity_ci'][0], 3)} to "
            f"{_fmt_num(m['sensitivity_ci'][1], 3)}), specificity "
            f"{_fmt_num(m['specificity'], 3)} (95% CI "
            f"{_fmt_num(m['specificity_ci'][0], 3)} to "
            f"{_fmt_num(m['specificity_ci'][1], 3)}); PPV "
            f"{_fmt_num(m['ppv'], 3)}, NPV {_fmt_num(m['npv'], 3)}; "
            f"LR+={_fmt_num(m.get('lr_pos'))}, LR-={_fmt_num(m.get('lr_neg'), 3)}."
        )
    else:
        methods = (
            f"Methods: Diagnostic accuracy of the dichotomous {test} was "
            f"assessed against {reference} using the standard 2x2 "
            f"contingency table. Sensitivity, specificity, predictive "
            f"values, and likelihood ratios are reported with Wilson 95% "
            f"confidence intervals."
        )
        m = result["metrics"]
        res = (
            f"Results: Among {result['n']} subjects "
            f"({result['n_positive']} positive by reference), {test} achieved "
            f"sensitivity {_fmt_num(m['sensitivity'], 3)} (95% CI "
            f"{_fmt_num(m['sensitivity_ci'][0], 3)} to "
            f"{_fmt_num(m['sensitivity_ci'][1], 3)}), specificity "
            f"{_fmt_num(m['specificity'], 3)} (95% CI "
            f"{_fmt_num(m['specificity_ci'][0], 3)} to "
            f"{_fmt_num(m['specificity_ci'][1], 3)}); PPV "
            f"{_fmt_num(m['ppv'], 3)}, NPV {_fmt_num(m['npv'], 3)}; "
            f"LR+={_fmt_num(m.get('lr_pos'))}, LR-={_fmt_num(m.get('lr_neg'), 3)}."
        )
    if "bayes" in result:
        b = result["bayes"]
        res += (
            f" At a pre-test probability of {_fmt_num(b['pre_test_probability'], 2)}, "
            f"the post-test probability is "
            f"{_fmt_num(b.get('post_test_prob_positive'), 3)} after a "
            f"positive test and {_fmt_num(b.get('post_test_prob_negative'), 3)} "
            f"after a negative test (Bayes)."
        )
    return {"methods": methods, "results": res}


def prose_agreement(
    result: dict[str, Any],
    *,
    display_labels: dict[str, str] | None = None,
) -> dict[str, str]:
    a = _label(result["rater_a"], display_labels)
    b = _label(result["rater_b"], display_labels)
    n = result["n_pairs"]
    if result["data_type"] == "continuous":
        icc = result["icc"]
        ba = result["bland_altman"]
        methods = (
            f"Methods: Inter-rater agreement between {a} and {b} was "
            f"quantified by the intraclass correlation coefficient (ICC; "
            f"two-way mixed, absolute agreement, single measurement) on "
            f"n={n} paired observations. Systematic bias and 95% limits of "
            f"agreement were assessed via the Bland-Altman approach."
        )
        ci = _fmt_ci(icc.get("ci_low"), icc.get("ci_high"), 3)
        results = (
            f"Results: ICC was {_fmt_num(icc['icc'], 3)} (95% CI {ci}; "
            f"{_fmt_p(icc['p_value'])}). The Bland-Altman mean bias was "
            f"{_fmt_num(ba['bias'])} with 95% limits of agreement "
            f"{_fmt_num(ba['loa_low'])} to {_fmt_num(ba['loa_high'])}."
        )
    else:
        k = result["kappa"]
        weighted = result.get("weighted_kappa")
        methods = (
            f"Methods: Agreement between {a} and {b} was quantified by "
            f"Cohen's kappa on n={n} paired observations."
            + (
                " A linearly weighted kappa was additionally computed to "
                "credit near-misses for ordinal data."
                if weighted is not None
                else ""
            )
        )
        ci = _fmt_ci(k.get("ci_low"), k.get("ci_high"), 3)
        bits = (
            f"kappa={_fmt_num(k['kappa'], 3)} (95% CI {ci}; observed "
            f"agreement {_fmt_num(k['po'], 3)}, expected agreement "
            f"{_fmt_num(k['pe'], 3)})"
        )
        if weighted:
            bits += f"; weighted kappa={_fmt_num(weighted['kappa'], 3)}"
        results = f"Results: {bits}."
    return {"methods": methods, "results": results}


PROSE_DISPATCH = {
    "two_group": prose_two_group,
    "risk_factors": prose_risk_factors,
    "survival": prose_survival,
    "diagnostic": prose_diagnostic,
    "agreement": prose_agreement,
}


def prose_for(
    result: dict[str, Any],
    *,
    display_labels: dict[str, str] | None = None,
) -> dict[str, str]:
    pathway = result.get("pathway")
    fn = PROSE_DISPATCH.get(pathway)  # type: ignore[arg-type]
    if fn is None:
        raise ValueError(f"unknown pathway in result: {pathway!r}")
    return fn(result, display_labels=display_labels)
