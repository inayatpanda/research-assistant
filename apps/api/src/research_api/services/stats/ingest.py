from __future__ import annotations

import io
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd
from openpyxl import load_workbook

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CSV_MIME = "text/csv"

_TIME_NAME_RE = re.compile(r"^(date|time|dt|admit|discharge|surgery|fu_|followup)", re.I)

_ORDINAL_TOKENS = {
    "mild",
    "moderate",
    "severe",
    "low",
    "medium",
    "high",
    "small",
    "large",
    "none",
    "minimal",
    "mild-moderate",
    "moderate-severe",
    "i",
    "ii",
    "iii",
    "iv",
    "v",
}


@dataclass(frozen=True)
class InferredColumn:
    name: str
    position: int
    inferred_type: str
    n_missing: int
    sample_values: list[str]


@dataclass(frozen=True)
class IngestResult:
    n_rows: int
    n_columns: int
    columns: list[InferredColumn]


def detect_table_mime(data: bytes) -> str:
    if not data:
        raise ValueError("empty payload")
    if data[:4] == b"PK\x03\x04" and (
        b"xl/workbook.xml" in data or b"[Content_Types]" in data
    ):
        return XLSX_MIME
    head = data[:1024].decode("utf-8", errors="ignore")
    if head and any(d in head for d in (",", ";", "\t")):
        if "\n" in head or "\r" in head or len(head) < 1024:
            return CSV_MIME
    raise ValueError("unsupported table mime")


def read_table(data: bytes, mime: str) -> pd.DataFrame:
    if mime == CSV_MIME:
        return pd.read_csv(io.BytesIO(data))
    if mime == XLSX_MIME:
        wb = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return pd.DataFrame()
        header = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
        body = rows[1:]
        df = pd.DataFrame(body, columns=header)
        return _coerce_obvious_numerics(df)
    raise ValueError(f"unsupported mime {mime}")


def _coerce_obvious_numerics(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        s = df[col]
        if s.dtype == object:
            non_null = s.dropna()
            if len(non_null) > 0 and all(isinstance(v, (int, float, np.integer, np.floating)) for v in non_null):
                df[col] = pd.to_numeric(s, errors="ignore")
    return df


def _looks_ordinal(values: list[str]) -> bool:
    lowered = [v.strip().lower() for v in values]
    if all(v.isdigit() for v in lowered) and len(set(lowered)) <= 10:
        return True
    if all(v in _ORDINAL_TOKENS for v in lowered):
        return True
    return False


def _stringify(v: object) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _distinct_non_null(series: pd.Series) -> list[object]:
    seen: list[object] = []
    s = set()
    for v in series.tolist():
        if v is None:
            continue
        if isinstance(v, float) and np.isnan(v):
            continue
        key = _stringify(v)
        if key in s:
            continue
        s.add(key)
        seen.append(v)
    return seen


def infer_columns(df: pd.DataFrame) -> list[InferredColumn]:
    out: list[InferredColumn] = []
    for pos, col in enumerate(df.columns):
        series = df[col]
        n_missing = int(series.isna().sum())
        distinct = _distinct_non_null(series)
        sample = [_stringify(v) for v in distinct[:5]]
        inferred = _infer_one(col, series, distinct)
        out.append(
            InferredColumn(
                name=str(col),
                position=pos,
                inferred_type=inferred,
                n_missing=n_missing,
                sample_values=sample,
            )
        )
    return out


def _infer_one(name: object, series: pd.Series, distinct: list[object]) -> str:
    if len(distinct) == 0:
        return "unknown"
    if len(distinct) == 1:
        return "unknown"

    if pd.api.types.is_datetime64_any_dtype(series):
        return "time"

    name_str = str(name)
    if _TIME_NAME_RE.match(name_str):
        sample = series.dropna().astype(str).head(5).tolist()
        if sample and all(_parseable_datetime(s) for s in sample):
            return "time"

    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    distinct_str = [_stringify(v) for v in distinct]

    if _looks_ordinal(distinct_str):
        return "ordinal"

    avg_len = (
        sum(len(s) for s in distinct_str) / max(1, len(distinct_str)) if distinct_str else 0
    )
    if len(distinct) <= 10 and avg_len <= 25:
        return "nominal"

    return "nominal"


def _parseable_datetime(s: str) -> bool:
    try:
        pd.to_datetime(s, errors="raise")
        return True
    except (ValueError, TypeError):
        return False


def ingest(data: bytes, mime: str) -> IngestResult:
    df = read_table(data, mime)
    columns = infer_columns(df)
    return IngestResult(
        n_rows=int(df.shape[0]),
        n_columns=int(df.shape[1]),
        columns=columns,
    )
