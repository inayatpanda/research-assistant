"""Tests for services/stats/charts/_base.py — Phase 8.5 Task 1."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from research_api.services.stats.charts._base import (  # noqa: E402
    fig_context,
    fig_to_data_uri,
    fig_to_png_bytes,
)


def test_fig_context_closes_figure_on_exit() -> None:
    with fig_context() as fig:
        assert fig in [plt.figure(num=n) for n in plt.get_fignums()]
    assert plt.get_fignums() == []


def test_fig_to_png_bytes_starts_with_png_magic() -> None:
    with fig_context() as fig:
        ax = fig.add_subplot(1, 1, 1)
        ax.plot([0, 1, 2], [0, 1, 4])
        out = fig_to_png_bytes(fig)
    assert out[:8] == b"\x89PNG\r\n\x1a\n"


def test_fig_to_data_uri_returns_expected_shape() -> None:
    with fig_context() as fig:
        ax = fig.add_subplot(1, 1, 1)
        ax.plot([0, 1], [1, 0])
        out = fig_to_data_uri(fig)
    assert set(out.keys()) == {"format", "data_uri", "byte_size"}
    assert out["format"] == "png"
    assert out["data_uri"].startswith("data:image/png;base64,")
    assert isinstance(out["byte_size"], int)
    assert out["byte_size"] > 0


def test_fig_context_closes_even_on_exception() -> None:
    try:
        with fig_context() as fig:
            assert fig is not None
            raise RuntimeError("boom")
    except RuntimeError:
        pass
    assert plt.get_fignums() == []


def test_repeated_calls_no_state_leak() -> None:
    for _ in range(10):
        with fig_context() as fig:
            ax = fig.add_subplot(1, 1, 1)
            ax.plot([0, 1], [1, 0])
            _ = fig_to_png_bytes(fig)
    assert plt.get_fignums() == []
