"""Phase 13 (MP13) — Cross-dataset op pure-function tests."""
from __future__ import annotations

import pandas as pd
import pytest

from research_api.services.stats.cross_dataset import (
    CrossDatasetError,
    append,
    join,
    merge,
)


def test_merge_inner_default():
    a = pd.DataFrame({"id": [1, 2, 3], "x": [10, 20, 30]})
    b = pd.DataFrame({"id": [2, 3, 4], "y": [200, 300, 400]})
    out = merge(a, b, on=["id"], how="inner")
    assert list(out["id"]) == [2, 3]
    assert list(out["x"]) == [20, 30]
    assert list(out["y"]) == [200, 300]


def test_merge_left_keeps_unmatched():
    a = pd.DataFrame({"id": [1, 2, 3], "x": [10, 20, 30]})
    b = pd.DataFrame({"id": [2, 3, 4], "y": [200, 300, 400]})
    out = merge(a, b, on=["id"], how="left")
    assert list(out["id"]) == [1, 2, 3]
    assert out.shape[0] == 3
    assert pd.isna(out["y"].iloc[0])


def test_merge_requires_columns():
    a = pd.DataFrame({"id": [1]})
    b = pd.DataFrame({"id": [1]})
    with pytest.raises(CrossDatasetError):
        merge(a, b, on=["ghost"], how="inner")


def test_merge_unknown_how_raises():
    a = pd.DataFrame({"id": [1]})
    b = pd.DataFrame({"id": [1]})
    with pytest.raises(CrossDatasetError):
        merge(a, b, on=["id"], how="cross")  # type: ignore[arg-type]


def test_merge_empty_on_raises():
    a = pd.DataFrame({"id": [1]})
    b = pd.DataFrame({"id": [1]})
    with pytest.raises(CrossDatasetError):
        merge(a, b, on=[], how="inner")


def test_append_two_frames_concatenates_rows():
    a = pd.DataFrame({"x": [1, 2]})
    b = pd.DataFrame({"x": [3, 4]})
    out = append(a, b)
    assert list(out["x"]) == [1, 2, 3, 4]
    assert out.shape[0] == 4


def test_append_unequal_columns_fills_nan():
    a = pd.DataFrame({"x": [1], "y": [2]})
    b = pd.DataFrame({"x": [3], "z": [4]})
    out = append(a, b)
    assert out.shape[0] == 2
    assert set(out.columns) == {"x", "y", "z"}
    # y missing in row from b
    assert pd.isna(out.loc[1, "y"])


def test_append_no_args_raises():
    with pytest.raises(CrossDatasetError):
        append()


def test_join_inner_on_index():
    a = pd.DataFrame({"id": [1, 2, 3], "x": [10, 20, 30]})
    b = pd.DataFrame({"id": [2, 3, 4], "y": [200, 300, 400]})
    out = join(a, b, on="id", how="inner")
    assert list(out["id"]) == [2, 3]


def test_join_requires_string_on():
    a = pd.DataFrame({"id": [1]})
    b = pd.DataFrame({"id": [1]})
    with pytest.raises(CrossDatasetError):
        join(a, b, on="", how="left")
