"""Tests for services/stats/charts/scatter_plot.py — Phase 8.5 Task 5."""
from __future__ import annotations

import base64

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from research_api.services.stats.charts.scatter_plot import (  # noqa: E402
    render_scatter_plot,
)


def _xy(n: int = 60, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n)
    y = 2.0 * x + rng.normal(0, 0.5, n)
    return pd.DataFrame({"x": x, "y": y})


def test_scatter_returns_data_uri_shape() -> None:
    out = render_scatter_plot(df=_xy(), x="x", y="y")
    assert set(out.keys()) == {"format", "data_uri", "byte_size"}
    assert out["data_uri"].startswith("data:image/png;base64,")


def test_scatter_png_magic_bytes() -> None:
    out = render_scatter_plot(df=_xy(), x="x", y="y")
    raw = base64.b64decode(out["data_uri"].split(",", 1)[1])
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"


def test_scatter_lowess_smooth_renders() -> None:
    out = render_scatter_plot(df=_xy(), x="x", y="y", fit="lowess")
    assert out["byte_size"] > 0


def test_scatter_no_ci_when_ci_none() -> None:
    out = render_scatter_plot(df=_xy(), x="x", y="y", ci=None)
    assert out["byte_size"] > 0


def test_scatter_handles_constant_predictor() -> None:
    df = pd.DataFrame({"x": [1.0] * 20, "y": np.random.default_rng(0).normal(0, 1, 20)})
    # Should not raise; fit line is suppressed.
    out = render_scatter_plot(df=df, x="x", y="y")
    assert out["byte_size"] > 0
    assert plt.get_fignums() == []
