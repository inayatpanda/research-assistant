"""F3 Pathway 3 — Time-to-event / survival analysis.

Always produces a Kaplan-Meier curve. When a stratum column is given,
also runs the log-rank test. When predictors are given, fits a Cox
proportional-hazards model and tests the PH assumption via Schoenfeld
residuals.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _km_summary(time: np.ndarray, event: np.ndarray) -> dict[str, Any]:
    from lifelines import KaplanMeierFitter

    kmf = KaplanMeierFitter().fit(time, event)
    sf = kmf.survival_function_
    times = [float(t) for t in sf.index.tolist()]
    survival = [float(v) for v in sf.iloc[:, 0].tolist()]
    median = float(kmf.median_survival_time_)
    return {
        "n": int(len(time)),
        "n_events": int(event.sum()),
        "median_survival": median if np.isfinite(median) else None,
        "times": times,
        "survival": survival,
    }


def run(
    df: pd.DataFrame,
    *,
    time: str,
    event: str,
    strata: str | None = None,
    predictors: list[str] | None = None,
) -> dict[str, Any]:
    if time not in df.columns:
        raise ValueError(f"time column '{time}' not in dataset")
    if event not in df.columns:
        raise ValueError(f"event column '{event}' not in dataset")
    use_cols = [time, event]
    if strata:
        if strata not in df.columns:
            raise ValueError(f"strata column '{strata}' not in dataset")
        use_cols.append(strata)
    predictors = list(predictors or [])
    for p in predictors:
        if p not in df.columns:
            raise ValueError(f"predictor '{p}' not in dataset")
    use_cols.extend(predictors)

    clean = df[list(dict.fromkeys(use_cols))].dropna().copy()
    if clean.empty:
        raise ValueError("no rows with non-missing time/event values")
    # Coerce.
    clean[time] = pd.to_numeric(clean[time], errors="coerce")
    clean[event] = pd.to_numeric(clean[event], errors="coerce")
    clean = clean.dropna(subset=[time, event])
    if clean.empty:
        raise ValueError("time/event values are not numeric")
    if (clean[time] < 0).any():
        raise ValueError("time values must be non-negative")
    event_vals = set(clean[event].unique().tolist())
    if not event_vals.issubset({0, 1, 0.0, 1.0}):
        raise ValueError("event column must contain only 0/1 values")
    if clean[event].sum() == 0:
        raise ValueError("no events observed; cannot fit survival model")

    out: dict[str, Any] = {
        "pathway": "survival",
        "time": time,
        "event": event,
        "strata": strata,
        "predictors": predictors,
        "n": int(len(clean)),
        "n_events": int(clean[event].sum()),
    }

    overall = _km_summary(
        clean[time].to_numpy(dtype=float), clean[event].to_numpy(dtype=float)
    )
    out["overall"] = overall

    if strata is not None:
        from lifelines.statistics import multivariate_logrank_test

        levels = sorted(clean[strata].astype(str).unique().tolist())
        per_stratum: dict[str, Any] = {}
        for lv in levels:
            sub = clean[clean[strata].astype(str) == lv]
            if len(sub) < 2:
                continue
            per_stratum[lv] = _km_summary(
                sub[time].to_numpy(dtype=float), sub[event].to_numpy(dtype=float)
            )
        out["per_stratum"] = per_stratum

        if len(levels) >= 2:
            try:
                lr = multivariate_logrank_test(
                    clean[time], clean[strata].astype(str), clean[event]
                )
                out["logrank"] = {
                    "test_statistic": float(lr.test_statistic),
                    "p_value": float(lr.p_value),
                    "df": float(len(levels) - 1),
                }
            except Exception as exc:  # noqa: BLE001
                out["logrank"] = {"error": str(exc)}

    if predictors:
        from lifelines import CoxPHFitter
        from lifelines.statistics import proportional_hazard_test

        fit_df = clean[[time, event] + predictors].copy()
        # One-hot any non-numeric predictors using pandas.
        non_numeric = [p for p in predictors if not pd.api.types.is_numeric_dtype(fit_df[p])]
        if non_numeric:
            fit_df = pd.get_dummies(
                fit_df, columns=non_numeric, drop_first=True
            )
        try:
            # Coerce dummy columns to float so lifelines accepts them.
            for col in fit_df.columns:
                if col in (time, event):
                    continue
                fit_df[col] = pd.to_numeric(fit_df[col], errors="coerce")
            fit_df = fit_df.dropna()
            cph = CoxPHFitter()
            cph.fit(fit_df, duration_col=time, event_col=event)
            summary = cph.summary
            rows: list[dict[str, Any]] = []
            for name in summary.index:
                rows.append(
                    {
                        "term": str(name),
                        "estimate": float(np.exp(summary.loc[name, "coef"])),
                        "estimate_label": "HR",
                        "ci_low": float(
                            np.exp(summary.loc[name, "coef lower 95%"])
                        ),
                        "ci_high": float(
                            np.exp(summary.loc[name, "coef upper 95%"])
                        ),
                        "p_value": float(summary.loc[name, "p"]),
                    }
                )
            out["cox"] = {
                "n": int(cph._n_examples),
                "concordance": float(cph.concordance_index_),
                "log_likelihood": float(cph.log_likelihood_),
                "terms": rows,
            }
            try:
                ph = proportional_hazard_test(cph, fit_df)
                ph_summary = ph.summary if hasattr(ph, "summary") else None
                if ph_summary is not None:
                    out["cox"]["ph_assumption"] = {
                        "p_values": {
                            str(idx): float(ph_summary.loc[idx, "p"])
                            for idx in ph_summary.index
                        },
                        "global_p": float(ph_summary["p"].min()),
                        "violated": bool(
                            (ph_summary["p"].min() < 0.05)
                        ),
                    }
                else:
                    out["cox"]["ph_assumption"] = {
                        "p_value": float(ph.p_value),
                        "violated": bool(float(ph.p_value) < 0.05),
                    }
            except Exception as exc:  # noqa: BLE001
                out["cox"]["ph_assumption"] = {"error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            out["cox"] = {"error": str(exc)}

    return out
