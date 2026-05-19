"""Phase 13 (MP13) — Cross-dataset ops.

Pure-function wrappers around pandas merge / append / join used to compose
new datasets from two or more sources. The result is always a NEW DataFrame
suitable for persisting via the storage backend.
"""
from __future__ import annotations

from typing import Literal

import pandas as pd

MergeHow = Literal["inner", "left", "right", "outer"]
JoinHow = Literal["inner", "left", "right", "outer"]


class CrossDatasetError(ValueError):
    """Raised when sources / args are structurally invalid."""


def _require_columns(df: pd.DataFrame, cols: list[str], label: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise CrossDatasetError(
            f"{label}: columns not in dataframe: {missing!r}"
        )


def merge(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    on: list[str],
    how: MergeHow = "inner",
) -> pd.DataFrame:
    if not on:
        raise CrossDatasetError("merge requires non-empty 'on'")
    _require_columns(df_a, on, "merge:left")
    _require_columns(df_b, on, "merge:right")
    if how not in ("inner", "left", "right", "outer"):
        raise CrossDatasetError(f"merge: unknown how={how!r}")
    return df_a.merge(df_b, on=on, how=how)


def append(*dfs: pd.DataFrame) -> pd.DataFrame:
    """Row-bind any number of DataFrames. Columns are aligned by name; missing
    columns become NaN in the result.
    """
    if not dfs:
        raise CrossDatasetError("append requires at least 1 frame")
    return pd.concat(list(dfs), axis=0, ignore_index=True, sort=False)


def join(
    df_a: pd.DataFrame,
    df_b: pd.DataFrame,
    on: str,
    how: JoinHow = "left",
) -> pd.DataFrame:
    """Index-based join after setting ``on`` as the index on both sides."""
    if not isinstance(on, str) or not on:
        raise CrossDatasetError("join requires a non-empty 'on' column name")
    _require_columns(df_a, [on], "join:left")
    _require_columns(df_b, [on], "join:right")
    if how not in ("inner", "left", "right", "outer"):
        raise CrossDatasetError(f"join: unknown how={how!r}")
    left = df_a.set_index(on)
    right = df_b.set_index(on)
    return left.join(right, how=how, lsuffix="", rsuffix="_y").reset_index()
