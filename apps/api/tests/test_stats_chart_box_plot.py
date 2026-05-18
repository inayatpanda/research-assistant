"""Tests for services/stats/charts/box_plot.py — Phase 8.5 Task 2."""
from __future__ import annotations

import base64

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from research_api.services.stats.charts.box_plot import render_box_plot  # noqa: E402


def _two_group_df(seed: int = 42, n: int = 30) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "y": np.concatenate([rng.normal(0, 1, n), rng.normal(1, 1, n)]),
            "g": ["A"] * n + ["B"] * n,
        }
    )


def test_box_plot_returns_data_uri_shape() -> None:
    df = _two_group_df()
    out = render_box_plot(df=df, outcome="y", groups="g")
    assert set(out.keys()) == {"format", "data_uri", "byte_size"}
    assert out["format"] == "png"
    assert out["data_uri"].startswith("data:image/png;base64,")
    assert out["byte_size"] > 100


def test_box_plot_png_magic_bytes() -> None:
    df = _two_group_df()
    out = render_box_plot(df=df, outcome="y", groups="g")
    raw = base64.b64decode(out["data_uri"].split(",", 1)[1])
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"


def test_box_plot_handles_two_groups() -> None:
    df = _two_group_df()
    out = render_box_plot(df=df, outcome="y", groups="g")
    assert out["byte_size"] > 0


def test_box_plot_handles_more_than_two_groups() -> None:
    rng = np.random.default_rng(11)
    n = 20
    df = pd.DataFrame(
        {
            "y": np.concatenate(
                [
                    rng.normal(0, 1, n),
                    rng.normal(1, 1, n),
                    rng.normal(2, 1, n),
                    rng.normal(3, 1, n),
                ]
            ),
            "g": ["A"] * n + ["B"] * n + ["C"] * n + ["D"] * n,
        }
    )
    out = render_box_plot(df=df, outcome="y", groups="g")
    assert out["byte_size"] > 0


def test_box_plot_dropna_does_not_crash_on_partial_nan_column() -> None:
    df = _two_group_df()
    df.loc[0:5, "y"] = np.nan
    out = render_box_plot(df=df, outcome="y", groups="g")
    assert out["byte_size"] > 0


def test_box_plot_raises_value_error_on_all_nan_group() -> None:
    df = pd.DataFrame({"y": [np.nan] * 10, "g": ["A"] * 5 + ["B"] * 5})
    with pytest.raises(ValueError):
        render_box_plot(df=df, outcome="y", groups="g")


def test_box_plot_no_matplotlib_state_leak() -> None:
    df = _two_group_df()
    for _ in range(5):
        render_box_plot(df=df, outcome="y", groups="g")
    assert plt.get_fignums() == []
