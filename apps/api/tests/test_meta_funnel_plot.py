"""Funnel plot renderer tests."""
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from research_api.services.meta.effect_sizes import Effect
from research_api.services.meta.funnel_plot import _build_figure, render_funnel_png


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _effects() -> list[Effect]:
    return [
        Effect(yi=0.5, vi=0.04, se=0.2, metric="md"),
        Effect(yi=0.3, vi=0.05, se=math.sqrt(0.05), metric="md"),
        Effect(yi=0.6, vi=0.02, se=math.sqrt(0.02), metric="md"),
        Effect(yi=0.4, vi=0.03, se=math.sqrt(0.03), metric="md"),
    ]


def test_funnel_renders_valid_png():
    out = render_funnel_png(
        effects=_effects(),
        pooled_estimate=0.45,
        metric_label="MD",
        log_scale=False,
    )
    assert out[:8] == _PNG_MAGIC
    assert len(out) > 1000


def test_funnel_handles_two_studies():
    eff = _effects()[:2]
    out = render_funnel_png(
        effects=eff,
        pooled_estimate=0.4,
        metric_label="MD",
        log_scale=False,
    )
    assert out[:8] == _PNG_MAGIC


def test_funnel_axis_inverted():
    fig = _build_figure(
        effects=_effects(),
        pooled_estimate=0.4,
        metric_label="MD",
        log_scale=False,
    )
    try:
        ax = fig.axes[0]
        assert bool(ax.yaxis_inverted()) is True
    finally:
        plt.close(fig)


def test_no_state_leak():
    for _ in range(5):
        render_funnel_png(
            effects=_effects(),
            pooled_estimate=0.4,
            metric_label="MD",
            log_scale=False,
        )
    assert plt.get_fignums() == []
