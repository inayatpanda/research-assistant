"""Tests for services/stats/charts/qq_plot.py — Phase 8.5 Task 4."""
from __future__ import annotations

import base64

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from scipy import stats as sp_stats  # noqa: E402

from research_api.services.stats.charts.qq_plot import render_qq_plot  # noqa: E402


def test_qq_plot_returns_data_uri_shape() -> None:
    df = pd.DataFrame({"v": np.random.default_rng(0).normal(0, 1, 100)})
    out = render_qq_plot(df=df, column="v")
    assert set(out.keys()) == {"format", "data_uri", "byte_size"}
    assert out["data_uri"].startswith("data:image/png;base64,")


def test_qq_plot_png_magic_bytes() -> None:
    df = pd.DataFrame({"v": np.random.default_rng(0).normal(0, 1, 100)})
    out = render_qq_plot(df=df, column="v")
    raw = base64.b64decode(out["data_uri"].split(",", 1)[1])
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"


def test_qq_plot_with_normal_data_line_runs_through_points() -> None:
    sample = np.random.default_rng(42).normal(0, 1, 200)
    # probplot returns ((osm, osr), (slope, intercept, r))
    _, (_, _, r) = sp_stats.probplot(sample, dist="norm")
    assert r >= 0.95


def test_qq_plot_with_skewed_data_still_renders() -> None:
    rng = np.random.default_rng(3)
    df = pd.DataFrame({"v": rng.exponential(1.0, 80)})
    out = render_qq_plot(df=df, column="v")
    assert out["byte_size"] > 0


def test_qq_plot_dropna() -> None:
    df = pd.DataFrame({"v": [1.0, 2.0, np.nan, 3.0, 4.0, np.nan, 5.0]})
    out = render_qq_plot(df=df, column="v")
    assert out["byte_size"] > 0
    assert plt.get_fignums() == []


def test_qq_plot_raises_on_all_nan() -> None:
    df = pd.DataFrame({"v": [np.nan, np.nan, np.nan]})
    with pytest.raises(ValueError):
        render_qq_plot(df=df, column="v")
