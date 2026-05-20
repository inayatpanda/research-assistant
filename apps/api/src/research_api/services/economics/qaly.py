"""Phase 18 (MP18) — QALY computation (area under the utility curve).

Trapezoidal integration of utility vs time per patient. ``time_col`` is in
*months*, the QALY is returned in *years* (months / 12). This matches the
convention used in the CRAFFT trial's CEA: utility measured at 0, 3, 6,
9, 12 months → AUC across 12 months → QALY.

With ``baseline_adjust=True`` we subtract each patient's baseline (t=0)
utility from every timepoint before integrating — the standard adjustment
for unbalanced baselines per Manca et al. 2005.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


_QALY_COL_DEFAULT = "qaly"


def compute_qaly(
    df: pd.DataFrame,
    *,
    utility_col: str,
    time_col: str,
    patient_col: str | None = None,
    group_col: str | None = None,
    baseline_adjust: bool = True,
    out_col: str = _QALY_COL_DEFAULT,
) -> pd.DataFrame:
    """Compute one QALY per patient via trapezoidal AUC.

    Parameters
    ----------
    df
        Long-format frame with one row per ``(patient, timepoint)``.
    utility_col
        Column holding the utility score [0..1] (or [-0.594..1] for EQ-5D).
    time_col
        Column holding the timepoint in **months** (numeric).
    patient_col
        Column identifying patients. If None we treat the entire frame as
        one patient (useful for unit tests / shape verification).
    group_col
        Optional treatment-group column; preserved in the output frame.
    baseline_adjust
        If True, subtract each patient's t=0 utility from every timepoint
        before integrating. The intercept-adjusted QALY is what enters
        the regression in cost_qaly_regression.bivariate_bootstrap.
    out_col
        Column name for the resulting per-patient QALY.

    Returns
    -------
    DataFrame with one row per patient: ``[patient_col, group_col, out_col]``
    (group_col only present if supplied).
    """
    if utility_col not in df.columns:
        raise ValueError(f"utility_col {utility_col!r} not in frame")
    if time_col not in df.columns:
        raise ValueError(f"time_col {time_col!r} not in frame")
    if patient_col is not None and patient_col not in df.columns:
        raise ValueError(f"patient_col {patient_col!r} not in frame")
    if group_col is not None and group_col not in df.columns:
        raise ValueError(f"group_col {group_col!r} not in frame")

    work = df[
        [c for c in (patient_col, group_col, time_col, utility_col) if c is not None]
    ].copy()
    work = work.dropna(subset=[time_col, utility_col])

    def _patient_qaly(sub: pd.DataFrame) -> float:
        sub = sub.sort_values(time_col)
        t = sub[time_col].to_numpy(dtype=float)
        u = sub[utility_col].to_numpy(dtype=float)
        if len(t) < 2:
            return float("nan")
        if baseline_adjust:
            # Take the earliest available row as baseline.
            u = u - u[0]
        # Trapezoidal AUC (months) → divide by 12 → years.
        # NumPy 2.0 renamed ``trapz`` to ``trapezoid``; fall back for older
        # versions so the service works on both.
        trap = getattr(np, "trapezoid", None) or np.trapz  # type: ignore[attr-defined]
        auc_months = trap(u, t)
        return float(auc_months / 12.0)

    if patient_col is None:
        qaly = _patient_qaly(work)
        out: dict = {out_col: [qaly]}
        if group_col is not None:
            out[group_col] = [work[group_col].iloc[0] if len(work) else None]
        return pd.DataFrame(out)

    rows: list[dict] = []
    grouped = work.groupby(patient_col, sort=False, dropna=False)
    for pid, sub in grouped:
        row: dict = {patient_col: pid, out_col: _patient_qaly(sub)}
        if group_col is not None:
            grp = sub[group_col].dropna()
            row[group_col] = grp.iloc[0] if len(grp) else None
        rows.append(row)
    cols = [patient_col, *( [group_col] if group_col else [] ), out_col]
    out_df = pd.DataFrame(rows, columns=cols)
    return out_df


__all__ = ["compute_qaly"]
