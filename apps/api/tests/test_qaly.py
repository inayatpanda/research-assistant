"""Phase 18 (MP18) — QALY AUC service tests."""
from __future__ import annotations

import pandas as pd
import pytest

from research_api.services.economics.qaly import compute_qaly


def _three_timepoint_frame(util_0, util_6, util_12, *, patient_id="p1", group="anterior"):
    return pd.DataFrame(
        {
            "patient_id": [patient_id] * 3,
            "group": [group] * 3,
            "time_months": [0, 6, 12],
            "utility": [util_0, util_6, util_12],
        }
    )


def test_qaly_constant_utility_one_year():
    """Constant utility 0.8 across 12 months → AUC = 0.8 * 12 / 12 = 0.8 QALY (no baseline-adjust)."""
    df = _three_timepoint_frame(0.8, 0.8, 0.8)
    out = compute_qaly(
        df,
        utility_col="utility",
        time_col="time_months",
        patient_col="patient_id",
        group_col="group",
        baseline_adjust=False,
    )
    assert len(out) == 1
    assert out["qaly"].iloc[0] == pytest.approx(0.8, abs=1e-9)


def test_qaly_three_point_average_specified_example():
    """Worked example from the plan: utility {0.8, 0.7, 0.6} at 0/6/12 months.

    Trapezoidal AUC across two 6-month panels:
      panel 0-6:  (0.8 + 0.7) / 2 * 6 = 4.5 utility-months
      panel 6-12: (0.7 + 0.6) / 2 * 6 = 3.9 utility-months
      total     = 8.4 utility-months
    QALY = 8.4 / 12 = 0.7. Plan claims ~0.708 because it expects an
    *uneven* schedule (e.g. four equally spaced points at 0/3/6/9/12);
    with the three-point schedule we land exactly on 0.7. Either is
    correct given the schedule; we lock the three-point answer here.
    """
    df = _three_timepoint_frame(0.8, 0.7, 0.6)
    out = compute_qaly(
        df,
        utility_col="utility",
        time_col="time_months",
        patient_col="patient_id",
        baseline_adjust=False,
    )
    assert out["qaly"].iloc[0] == pytest.approx(0.7, abs=1e-9)


def test_qaly_baseline_adjust_subtracts_zero():
    """Baseline-adjusted QALY = AUC of (u(t) - u(0)) / 12."""
    df = _three_timepoint_frame(0.8, 0.7, 0.6)
    out = compute_qaly(
        df,
        utility_col="utility",
        time_col="time_months",
        patient_col="patient_id",
        baseline_adjust=True,
    )
    # Subtracted profile: 0.0, -0.1, -0.2.
    # panel 0-6:  (0.0 + -0.1)/2 * 6 = -0.3
    # panel 6-12: (-0.1 + -0.2)/2 * 6 = -0.9
    # total      = -1.2 ; /12 = -0.1
    assert out["qaly"].iloc[0] == pytest.approx(-0.1, abs=1e-9)


def test_qaly_multiple_patients_independent():
    """Two patients → two QALYs, indexed in input order."""
    df = pd.concat(
        [
            _three_timepoint_frame(0.9, 0.9, 0.9, patient_id="p1", group="anterior"),
            _three_timepoint_frame(0.6, 0.6, 0.6, patient_id="p2", group="control"),
        ],
        ignore_index=True,
    )
    out = compute_qaly(
        df,
        utility_col="utility",
        time_col="time_months",
        patient_col="patient_id",
        group_col="group",
        baseline_adjust=False,
    )
    out = out.sort_values("patient_id").reset_index(drop=True)
    assert out["qaly"].iloc[0] == pytest.approx(0.9, abs=1e-9)
    assert out["qaly"].iloc[1] == pytest.approx(0.6, abs=1e-9)
    assert set(out["group"]) == {"anterior", "control"}


def test_qaly_missing_columns_errors():
    df = pd.DataFrame({"time_months": [0, 12], "utility": [1.0, 1.0]})
    with pytest.raises(ValueError, match="patient_col"):
        compute_qaly(
            df,
            utility_col="utility",
            time_col="time_months",
            patient_col="missing",
        )
    with pytest.raises(ValueError, match="utility_col"):
        compute_qaly(df, utility_col="missing", time_col="time_months")


def test_qaly_single_timepoint_yields_nan():
    """A patient with only one measurement has no AUC → NaN (not a crash)."""
    df = pd.DataFrame(
        {"patient_id": ["p1"], "time_months": [0], "utility": [0.8]}
    )
    out = compute_qaly(
        df, utility_col="utility", time_col="time_months", patient_col="patient_id"
    )
    assert pd.isna(out["qaly"].iloc[0])
