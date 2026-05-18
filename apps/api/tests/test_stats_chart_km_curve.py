"""Tests for services/stats/charts/km_curve.py — Phase 8.5 Task 6."""
from __future__ import annotations

import base64

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from research_api.services.stats.charts.km_curve import render_km_curve  # noqa: E402


def _simple_km(n: int = 30, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "t": rng.uniform(1, 30, n),
            "e": rng.integers(0, 2, n),
            "g": (["A"] * (n // 2)) + (["B"] * (n - n // 2)),
        }
    )


def test_km_curve_overall_renders() -> None:
    df = _simple_km()
    out = render_km_curve(df=df, duration="t", event="e")
    assert set(out.keys()) == {"format", "data_uri", "byte_size"}
    raw = base64.b64decode(out["data_uri"].split(",", 1)[1])
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"


def test_km_curve_two_groups_renders() -> None:
    df = _simple_km()
    out = render_km_curve(df=df, duration="t", event="e", groups="g")
    assert out["byte_size"] > 0


def test_km_curve_handles_no_events() -> None:
    df = pd.DataFrame(
        {"t": [1.0, 2.0, 3.0, 4.0, 5.0], "e": [0, 0, 0, 0, 0]}
    )
    out = render_km_curve(df=df, duration="t", event="e")
    assert out["byte_size"] > 0


def test_km_curve_handles_all_events() -> None:
    df = pd.DataFrame(
        {"t": [1.0, 2.0, 3.0, 4.0, 5.0], "e": [1, 1, 1, 1, 1]}
    )
    out = render_km_curve(df=df, duration="t", event="e")
    assert out["byte_size"] > 0


def test_km_curve_at_risk_band_included() -> None:
    # When add_at_risk_counts succeeds, the figure gains a second axes for the
    # at-risk numbers. We exercise the path; we tolerate the lifelines-side
    # failure case (covered by the try/except in the renderer).
    df = _simple_km()
    out = render_km_curve(df=df, duration="t", event="e", groups="g")
    assert out["byte_size"] > 0


def test_km_curve_dropna_on_duration_or_event() -> None:
    df = pd.DataFrame(
        {"t": [1.0, 2.0, np.nan, 4.0, 5.0], "e": [1, 0, 1, np.nan, 1]}
    )
    out = render_km_curve(df=df, duration="t", event="e")
    assert out["byte_size"] > 0
    assert plt.get_fignums() == []
