"""Multi-sheet XLSX ingest + long-format hint coverage (stats-refine)."""
from __future__ import annotations

import io

import numpy as np
import pandas as pd
import pytest
from openpyxl import Workbook

from research_api.services.stats.ingest import (
    detect_long_format,
    ingest,
    list_xlsx_sheets,
    read_table,
)

XLSX_MIME = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def _make_workbook(sheets: dict[str, list[list[object]]]) -> bytes:
    wb = Workbook()
    # remove default sheet
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        for r in rows:
            ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_list_xlsx_sheets_returns_all_in_order():
    data = _make_workbook(
        {
            "Demographics": [["age", "sex"], [40, "M"], [55, "F"]],
            "Outcomes": [["t", "score"], [0, 70], [1, 80]],
            "Costs": [["item", "gbp"], ["x", 100]],
        }
    )
    names = list_xlsx_sheets(data)
    assert names == ["Demographics", "Outcomes", "Costs"]


def test_list_xlsx_sheets_on_csv_returns_empty():
    assert list_xlsx_sheets(b"a,b\n1,2\n") == []


def test_list_xlsx_sheets_on_garbage_returns_empty():
    assert list_xlsx_sheets(b"\x00\x01\x02") == []


def test_read_table_with_sheet_name():
    data = _make_workbook(
        {
            "First": [["a"], [1], [2]],
            "Second": [["b"], [10], [20]],
        }
    )
    df1 = read_table(data, XLSX_MIME, sheet_name="First")
    df2 = read_table(data, XLSX_MIME, sheet_name="Second")
    assert list(df1.columns) == ["a"]
    assert list(df2.columns) == ["b"]
    assert df2.iloc[0, 0] in (10, 10.0)


def test_read_table_invalid_sheet_falls_back_to_active():
    data = _make_workbook(
        {
            "First": [["a"], [1]],
            "Second": [["b"], [10]],
        }
    )
    df = read_table(data, XLSX_MIME, sheet_name="DoesNotExist")
    # Falls back to active = first sheet.
    assert list(df.columns) == ["a"]


def test_ingest_includes_long_format_hint_for_repeated_measures():
    # 30 rows: 6 subjects × 5 timepoints, with a numeric outcome
    rows: list[list[object]] = []
    for pid in range(1, 7):
        for tp in range(5):
            rows.append([pid, tp, 50 + pid + tp])
    df = pd.DataFrame(rows, columns=["patient_id", "timepoint", "hhs"])
    hint = detect_long_format(df)
    assert hint is not None
    assert hint["subject_col"] == "patient_id"
    assert hint["time_col"] == "timepoint"
    assert hint["n_subjects"] == 6
    assert hint["n_per_subject"] == 5.0


def test_detect_long_format_returns_none_for_wide_data():
    df = pd.DataFrame(
        {
            "patient_id": [1, 2, 3, 4],
            "age": [40, 50, 60, 70],
            "hhs_pre": [50, 55, 60, 65],
            "hhs_post": [80, 82, 88, 85],
        }
    )
    # No time-like column → no hint.
    assert detect_long_format(df) is None


def test_detect_long_format_skips_when_no_numeric_outcome():
    rows: list[list[object]] = []
    for pid in range(1, 5):
        for tp in range(3):
            rows.append([pid, f"t{tp}"])
    df = pd.DataFrame(rows, columns=["patient_id", "timepoint"])
    assert detect_long_format(df) is None


def test_detect_long_format_handles_empty_or_tiny():
    assert detect_long_format(pd.DataFrame()) is None
    assert detect_long_format(pd.DataFrame({"x": [1]})) is None


def test_ingest_xlsx_with_explicit_sheet_includes_hint():
    data = _make_workbook(
        {
            "Demographics": [["pid", "age"], [1, 40], [2, 50], [3, 60]],
            "Outcomes_Long": [
                ["patient_id", "timepoint", "hhs"],
                *[
                    [pid, tp, 50 + pid + tp]
                    for pid in range(1, 7)
                    for tp in range(5)
                ],
            ],
        }
    )
    res = ingest(data, XLSX_MIME, sheet_name="Outcomes_Long")
    assert res.n_rows == 30
    assert res.long_format_hint is not None
    assert res.long_format_hint["subject_col"] == "patient_id"


def test_ingest_xlsx_single_sheet_backward_compat():
    data = _make_workbook(
        {
            "Demographics": [["pid", "age"], [1, 40], [2, 50]],
        }
    )
    res = ingest(data, XLSX_MIME)
    assert res.n_rows == 2
    assert res.long_format_hint is None
