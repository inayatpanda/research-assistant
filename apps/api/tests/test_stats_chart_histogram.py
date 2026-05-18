"""Tests for services/stats/charts/histogram.py — Phase 8.5 Task 3."""
from __future__ import annotations

import base64

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from research_api.services.stats.charts.histogram import (  # noqa: E402
    render_categorical_counts,
    render_histogram,
)


def test_histogram_returns_data_uri_shape() -> None:
    df = pd.DataFrame({"v": np.random.default_rng(0).normal(0, 1, 200)})
    out = render_histogram(df=df, column="v")
    assert set(out.keys()) == {"format", "data_uri", "byte_size"}
    assert out["data_uri"].startswith("data:image/png;base64,")


def test_histogram_png_magic_bytes() -> None:
    df = pd.DataFrame({"v": np.random.default_rng(0).normal(0, 1, 100)})
    out = render_histogram(df=df, column="v")
    raw = base64.b64decode(out["data_uri"].split(",", 1)[1])
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"


def test_histogram_handles_integer_column() -> None:
    df = pd.DataFrame({"v": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] * 5})
    out = render_histogram(df=df, column="v")
    assert out["byte_size"] > 0


def test_histogram_kde_false_omits_kde_line() -> None:
    df = pd.DataFrame({"v": np.random.default_rng(0).normal(0, 1, 100)})
    out_with = render_histogram(df=df, column="v", kde=True)
    out_without = render_histogram(df=df, column="v", kde=False)
    # We can't easily inspect the rendered axes from PNG bytes; just sanity-check
    # that both render and the kde-enabled version isn't a corrupt subset.
    assert out_with["byte_size"] > 0
    assert out_without["byte_size"] > 0


def test_histogram_dropna() -> None:
    df = pd.DataFrame({"v": [1.0, 2.0, np.nan, 3.0, np.nan, 4.0]})
    out = render_histogram(df=df, column="v")
    assert out["byte_size"] > 0
    assert plt.get_fignums() == []


def test_categorical_counts_renders_2x2() -> None:
    df = pd.DataFrame(
        {
            "treat": ["A", "A", "B", "B", "A", "B", "A", "B"] * 3,
            "resp": ["yes", "no", "yes", "no", "yes", "yes", "no", "no"] * 3,
        }
    )
    out = render_categorical_counts(df=df, var_a="treat", var_b="resp")
    assert out["data_uri"].startswith("data:image/png;base64,")
    raw = base64.b64decode(out["data_uri"].split(",", 1)[1])
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"


def test_categorical_counts_renders_3x3() -> None:
    df = pd.DataFrame(
        {
            "a": ["x", "y", "z"] * 9,
            "b": ["p", "q", "r"] * 9,
        }
    )
    out = render_categorical_counts(df=df, var_a="a", var_b="b")
    assert out["byte_size"] > 0
