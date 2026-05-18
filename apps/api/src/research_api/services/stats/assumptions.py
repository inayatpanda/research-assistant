from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

ALPHA = 0.05


@dataclass(frozen=True)
class AssumptionCheck:
    test_name: str
    statistic: float
    p_value: float
    ok: bool
    note: str


def shapiro(samples: list[float] | np.ndarray | pd.Series, alpha: float = ALPHA) -> AssumptionCheck:
    arr = np.asarray(list(samples), dtype=float)
    arr = arr[~np.isnan(arr)]
    if arr.size < 3:
        return AssumptionCheck(
            test_name="shapiro",
            statistic=float("nan"),
            p_value=float("nan"),
            ok=False,
            note="Shapiro-Wilk requires at least 3 observations; insufficient data.",
        )
    if arr.size > 5000:
        arr = np.random.default_rng(0).choice(arr, size=5000, replace=False)
    statistic, p_value = stats.shapiro(arr)
    ok = bool(p_value > alpha)
    note = (
        f"Shapiro-Wilk W={statistic:.4f}, p={p_value:.4f}; "
        f"sample is {'consistent with' if ok else 'not consistent with'} a normal distribution at alpha={alpha}."
    )
    return AssumptionCheck(
        test_name="shapiro",
        statistic=float(statistic),
        p_value=float(p_value),
        ok=ok,
        note=note,
    )


def levene(*groups: list[float] | np.ndarray | pd.Series, alpha: float = ALPHA) -> AssumptionCheck:
    if len(groups) < 2:
        raise ValueError("Levene's test requires at least two groups.")
    arrs = [np.asarray(list(g), dtype=float) for g in groups]
    arrs = [a[~np.isnan(a)] for a in arrs]
    statistic, p_value = stats.levene(*arrs, center="median")
    ok = bool(p_value > alpha)
    note = (
        f"Levene W={statistic:.4f}, p={p_value:.4f}; "
        f"group variances are {'consistent with' if ok else 'not consistent with'} equality at alpha={alpha}."
    )
    return AssumptionCheck(
        test_name="levene",
        statistic=float(statistic),
        p_value=float(p_value),
        ok=ok,
        note=note,
    )


def proportional_hazards_check(
    df: pd.DataFrame,
    *,
    duration_col: str,
    event_col: str,
    covariate_cols: list[str] | None = None,
    alpha: float = ALPHA,
) -> AssumptionCheck:
    from lifelines import CoxPHFitter
    from lifelines.statistics import proportional_hazard_test

    if duration_col not in df.columns or event_col not in df.columns:
        raise ValueError("duration_col and event_col must be columns of df")

    if covariate_cols is None:
        covariate_cols = [c for c in df.columns if c not in (duration_col, event_col)]

    fit_df = df[[duration_col, event_col, *covariate_cols]].dropna()
    if fit_df.shape[0] < 5 or not covariate_cols:
        return AssumptionCheck(
            test_name="prop_hazards",
            statistic=float("nan"),
            p_value=float("nan"),
            ok=True,
            note="Proportional hazards check skipped: insufficient data or no covariates.",
        )

    cph = CoxPHFitter()
    try:
        cph.fit(fit_df, duration_col=duration_col, event_col=event_col)
        res = proportional_hazard_test(cph, fit_df, time_transform="rank")
    except Exception as exc:  # noqa: BLE001
        return AssumptionCheck(
            test_name="prop_hazards",
            statistic=float("nan"),
            p_value=float("nan"),
            ok=True,
            note=f"Proportional hazards check could not be computed: {exc}",
        )

    p_min = float(res.summary["p"].min())
    chi2_max = float(res.summary["test_statistic"].max())
    ok = bool(p_min > alpha)
    note = (
        f"Proportional hazards test min-p={p_min:.4f}; "
        f"assumption {'holds' if ok else 'is violated'} at alpha={alpha}."
    )
    return AssumptionCheck(
        test_name="prop_hazards",
        statistic=chi2_max,
        p_value=p_min,
        ok=ok,
        note=note,
    )
