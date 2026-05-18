"""Phase 13 — OLS regression diagnostic plot shape tests.

Each of the four panels must return a valid PNG (magic-byte prefix). We
also assert the runner-level integration emits panels under chart["panels"]
keyed by exactly the four expected names.
"""
from __future__ import annotations

import base64

import numpy as np
import pandas as pd
import pytest

from research_api.services.stats.diagnostics import ols_diagnostic_plots
from research_api.services.stats.runner import run as runner_run


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _make_df(n: int = 60, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 1, n)
    z = rng.normal(0, 1, n)
    y = 2.0 * x - 0.5 * z + rng.normal(0, 1, n)
    return pd.DataFrame({"x": x, "z": z, "y": y})


def test_diagnostics_returns_four_panel_keys():
    df = _make_df()
    panels = ols_diagnostic_plots(df, "y", ["x"])
    assert set(panels.keys()) == {
        "residuals_vs_fitted",
        "qq",
        "scale_location",
        "residuals_vs_leverage",
    }


@pytest.mark.parametrize(
    "panel",
    ["residuals_vs_fitted", "qq", "scale_location", "residuals_vs_leverage"],
)
def test_diagnostics_panel_is_valid_png(panel: str):
    df = _make_df()
    panels = ols_diagnostic_plots(df, "y", ["x"])
    raw = panels[panel]
    assert isinstance(raw, bytes)
    assert raw.startswith(PNG_MAGIC), f"{panel} is not a PNG"
    assert len(raw) > 1000, f"{panel} unexpectedly tiny"


def test_diagnostics_handles_multiple_predictors():
    df = _make_df()
    panels = ols_diagnostic_plots(df, "y", ["x", "z"])
    assert all(v.startswith(PNG_MAGIC) for v in panels.values())


def test_diagnostics_raises_on_unknown_column():
    df = _make_df()
    with pytest.raises(ValueError):
        ols_diagnostic_plots(df, "y", ["nope"])


def test_diagnostics_raises_on_too_few_rows():
    df = _make_df(n=3)
    with pytest.raises(ValueError):
        ols_diagnostic_plots(df, "y", ["x"])


def test_runner_extends_ols_chart_with_panels():
    """The Phase 13 chart-shape extension is `chart["panels"][panel_name]`."""
    df = _make_df()
    res = runner_run(
        test_key="linear_regression",
        df=df,
        variables={"outcome": "y", "predictors": ["x"]},
    )
    assert res.chart is not None
    # Existing scatter chart is preserved at the top level.
    assert res.chart.get("format") == "png"
    assert "data_uri" in res.chart
    # New: panels dict under a separate key, four entries.
    panels = res.chart.get("panels")
    assert panels is not None
    assert set(panels.keys()) == {
        "residuals_vs_fitted",
        "qq",
        "scale_location",
        "residuals_vs_leverage",
    }
    raw = base64.b64decode(panels["qq"].split(",", 1)[1])
    assert raw.startswith(PNG_MAGIC)
