from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research_api.services.stats.ingest import (
    InferredColumn,
    IngestResult,
    detect_table_mime,
    infer_columns,
    ingest,
    read_table,
)

FIX = Path(__file__).parent / "fixtures"


def test_detect_table_mime_csv():
    csv = b"age,group\n45,A\n50,B\n"
    assert detect_table_mime(csv) == "text/csv"


def test_detect_table_mime_csv_with_semicolons():
    csv = b"age;group\n45;A\n"
    assert detect_table_mime(csv) == "text/csv"


def test_detect_table_mime_xlsx():
    data = (FIX / "tiny.xlsx").read_bytes()
    assert detect_table_mime(data) == (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def test_detect_table_mime_rejects_pdf():
    with pytest.raises(ValueError):
        detect_table_mime(b"%PDF-1.4\n%random stuff")


def test_detect_table_mime_rejects_empty():
    with pytest.raises(ValueError):
        detect_table_mime(b"")


def test_read_table_csv():
    csv = b"age,group\n45,A\n50,B\n"
    df = read_table(csv, "text/csv")
    assert list(df.columns) == ["age", "group"]
    assert df.shape == (2, 2)


def test_read_table_xlsx_data_only():
    data = (FIX / "tiny_with_formula.xlsx").read_bytes()
    df = read_table(
        data,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert list(df.columns) == ["a", "b"]
    assert df.iloc[0, 1] in (2, 2.0)
    assert df.iloc[1, 1] in (6, 6.0)
    for v in df["b"]:
        assert not (isinstance(v, str) and v.startswith("="))


def test_read_table_unknown_mime_raises():
    with pytest.raises(ValueError):
        read_table(b"x", "application/octet-stream")


def test_infer_numeric_column():
    df = pd.DataFrame({"age": [30, 45, 60, 72]})
    cols = infer_columns(df)
    assert cols[0].inferred_type == "numeric"
    assert cols[0].n_missing == 0


def test_infer_binary_numeric_event_eligible():
    df = pd.DataFrame({"died": [0, 1, 0, 1, 0]})
    cols = infer_columns(df)
    assert cols[0].inferred_type == "numeric"
    assert set(cols[0].sample_values).issubset({"0", "1"})


def test_infer_nominal_column():
    df = pd.DataFrame({"sex": ["M", "F", "M", "F", "M"]})
    cols = infer_columns(df)
    assert cols[0].inferred_type == "nominal"


def test_infer_ordinal_likert_strings():
    df = pd.DataFrame({"severity": ["mild", "moderate", "severe", "mild", "moderate"]})
    cols = infer_columns(df)
    assert cols[0].inferred_type == "ordinal"


def test_infer_ordinal_integers_as_strings():
    df = pd.DataFrame({"asa": ["1", "2", "3", "2", "1"]})
    cols = infer_columns(df)
    assert cols[0].inferred_type == "ordinal"


def test_infer_time_by_dtype():
    df = pd.DataFrame({"surgery_date": pd.to_datetime(["2024-01-01", "2024-02-15"])})
    cols = infer_columns(df)
    assert cols[0].inferred_type == "time"


def test_infer_time_by_name():
    df = pd.DataFrame({"admit_date": ["2024-01-01", "2024-02-15", "2024-03-01"]})
    cols = infer_columns(df)
    assert cols[0].inferred_type == "time"


def test_infer_unknown_for_all_nan_column():
    df = pd.DataFrame({"empty": [np.nan, np.nan, np.nan]})
    cols = infer_columns(df)
    assert cols[0].inferred_type == "unknown"


def test_infer_unknown_for_single_unique_value():
    df = pd.DataFrame({"all_one": ["x", "x", "x", "x"]})
    cols = infer_columns(df)
    assert cols[0].inferred_type == "unknown"


def test_n_missing_counted():
    df = pd.DataFrame({"x": [1.0, np.nan, 3.0, np.nan]})
    cols = infer_columns(df)
    assert cols[0].n_missing == 2


def test_sample_values_first_five_distinct():
    df = pd.DataFrame({"x": ["a", "b", "b", "c", "d", "e", "f", "g"]})
    cols = infer_columns(df)
    assert cols[0].sample_values[:5] == ["a", "b", "c", "d", "e"]


def test_sample_values_skip_nan():
    df = pd.DataFrame({"x": [np.nan, "a", "b", np.nan, "c"]})
    cols = infer_columns(df)
    assert "nan" not in [s.lower() for s in cols[0].sample_values]
    assert cols[0].sample_values[:3] == ["a", "b", "c"]


def test_infer_high_cardinality_string_is_nominal():
    df = pd.DataFrame({"note": [f"freetext_{i}_long_value" for i in range(20)]})
    cols = infer_columns(df)
    assert cols[0].inferred_type == "nominal"


def test_columns_keep_position():
    df = pd.DataFrame(
        {"age": [1, 2], "group": ["A", "B"], "score": [3.1, 4.2]}
    )
    cols = infer_columns(df)
    assert [c.position for c in cols] == [0, 1, 2]
    assert [c.name for c in cols] == ["age", "group", "score"]


def test_ingest_csv_returns_full_result():
    csv = b"age,group\n45,A\n50,B\n55,A\n"
    res = ingest(csv, "text/csv")
    assert isinstance(res, IngestResult)
    assert res.n_rows == 3
    assert res.n_columns == 2
    assert len(res.columns) == 2
    assert res.columns[0].inferred_type == "numeric"
    assert res.columns[1].inferred_type == "nominal"


def test_ingest_xlsx_smoke():
    data = (FIX / "tiny.xlsx").read_bytes()
    res = ingest(
        data,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert res.n_rows == 3
    assert res.n_columns == 2
    names = [c.name for c in res.columns]
    assert names == ["age", "group"]


def test_infer_mixed_dtype_string_object_is_nominal_or_ordinal():
    df = pd.DataFrame({"mix": ["1", "two", "3", "four"]})
    cols = infer_columns(df)
    assert cols[0].inferred_type in ("nominal", "ordinal")


def test_inferred_column_is_frozen_dataclass():
    c = InferredColumn(
        name="x", position=0, inferred_type="numeric", n_missing=0, sample_values=[]
    )
    with pytest.raises(Exception):
        c.name = "y"  # type: ignore[misc]


def test_csv_with_missing_values_in_numeric_column():
    csv = b"x,y\n1,a\n,b\n3,c\n4,\n"
    res = ingest(csv, "text/csv")
    assert res.columns[0].inferred_type == "numeric"
    assert res.columns[0].n_missing == 1
    assert res.columns[1].n_missing == 1
