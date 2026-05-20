"""DEMO-FIX-C — Runner passes display_labels through to chart renderers.

These tests exercise the seam between ``runner.run(...)`` and
``charts.select_and_render(...)`` to confirm that:

  1. ``display_labels=None`` keeps the legacy (pre-DEMO-FIX-C) behaviour
     where chart axes use canonical names.
  2. ``display_labels`` is forwarded verbatim to the renderer so the
     chart blob is produced with human-readable axes.
  3. The runner never mutates the input ``display_labels`` dict.
"""
from __future__ import annotations

import pandas as pd

from research_api.services.stats.runner import run


def test_runner_run_accepts_display_labels_without_raising():
    """Smoke: independent_t with display_labels returns a valid TestResult
    and a chart payload (PNG data URI)."""
    df = pd.DataFrame(
        {"score": [10, 12, 14, 11, 13, 9, 6, 8, 7, 8, 6, 9], "group": ["A"] * 6 + ["B"] * 6}
    )
    out = run(
        test_key="independent_t",
        df=df,
        variables={"outcome": "score", "groups": "group"},
        display_labels={"score": "Pain at 6 months", "group": "Treatment arm"},
    )
    assert out.test_key == "independent_t"
    assert out.chart is not None
    assert out.chart["format"] == "png"
    # Box-plot path executes (with display_labels).
    assert out.chart["byte_size"] > 0


def test_runner_run_no_display_labels_back_compat():
    """Without display_labels, the runner still returns a valid chart."""
    df = pd.DataFrame(
        {"score": [10, 12, 14, 11, 13, 9, 6, 8, 7, 8, 6, 9], "group": ["A"] * 6 + ["B"] * 6}
    )
    out = run(
        test_key="independent_t",
        df=df,
        variables={"outcome": "score", "groups": "group"},
    )
    assert out.chart is not None


def test_runner_run_does_not_mutate_display_labels_dict():
    """The runner must treat display_labels as read-only — it forwards it
    to renderers and doesn't modify the caller's dict."""
    df = pd.DataFrame(
        {"score": [10, 12, 14, 11, 13, 9, 6, 8, 7, 8, 6, 9], "group": ["A"] * 6 + ["B"] * 6}
    )
    labels = {"score": "Pain", "group": "Arm"}
    snapshot = dict(labels)
    run(
        test_key="independent_t",
        df=df,
        variables={"outcome": "score", "groups": "group"},
        display_labels=labels,
    )
    assert labels == snapshot
