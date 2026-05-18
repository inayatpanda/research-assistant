"""Forest plot renderer tests — PNG bytes + matplotlib state hygiene."""
import matplotlib

matplotlib.use("Agg")  # ensure non-interactive backend in test process
import matplotlib.pyplot as plt
import pytest

from research_api.services.meta.forest_plot import ForestRow, _build_figure, render_forest_png


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _rows() -> list[ForestRow]:
    return [
        ForestRow(label="Smith 2020", yi=0.5, ci_low=0.1, ci_high=0.9, weight_pct=40.0, subgroup=None),
        ForestRow(label="Lee 2021", yi=0.3, ci_low=-0.1, ci_high=0.7, weight_pct=30.0, subgroup=None),
        ForestRow(label="Wong 2022", yi=0.6, ci_low=0.2, ci_high=1.0, weight_pct=30.0, subgroup=None),
    ]


def test_renders_png_with_valid_magic_bytes():
    out = render_forest_png(
        rows=_rows(),
        pooled_estimate=0.46,
        pooled_ci_low=0.2,
        pooled_ci_high=0.7,
        metric_label="Standardised mean difference",
        log_scale=False,
        favours_left="Favours intervention",
        favours_right="Favours control",
    )
    assert out[:8] == _PNG_MAGIC


def test_renders_non_empty():
    out = render_forest_png(
        rows=_rows(),
        pooled_estimate=0.46,
        pooled_ci_low=0.2,
        pooled_ci_high=0.7,
        metric_label="SMD",
        log_scale=False,
        favours_left=None,
        favours_right=None,
    )
    assert len(out) > 1000


def test_handles_single_study_no_subgroup():
    one = [ForestRow(label="Only", yi=0.1, ci_low=-0.1, ci_high=0.3, weight_pct=100.0, subgroup=None)]
    out = render_forest_png(
        rows=one,
        pooled_estimate=0.1,
        pooled_ci_low=-0.1,
        pooled_ci_high=0.3,
        metric_label="MD",
        log_scale=False,
        favours_left=None,
        favours_right=None,
    )
    assert out[:8] == _PNG_MAGIC


def test_subgroup_blocks_produce_more_rows_in_image_height():
    sub_rows = [
        ForestRow(label="A1", yi=0.1, ci_low=-0.1, ci_high=0.3, weight_pct=25.0, subgroup="RCT"),
        ForestRow(label="A2", yi=0.2, ci_low=0.0, ci_high=0.4, weight_pct=25.0, subgroup="RCT"),
        ForestRow(label="B1", yi=0.5, ci_low=0.3, ci_high=0.7, weight_pct=25.0, subgroup="Cohort"),
        ForestRow(label="B2", yi=0.6, ci_low=0.4, ci_high=0.8, weight_pct=25.0, subgroup="Cohort"),
    ]
    subgroup_summary = {
        "RCT": (0.15, 0.0, 0.3),
        "Cohort": (0.55, 0.4, 0.7),
    }
    fig_with_sub = _build_figure(
        rows=sub_rows,
        pooled_estimate=0.35,
        pooled_ci_low=0.1,
        pooled_ci_high=0.6,
        metric_label="MD",
        log_scale=False,
        favours_left=None,
        favours_right=None,
        subgroup_summaries=subgroup_summary,
    )
    fig_plain = _build_figure(
        rows=sub_rows,
        pooled_estimate=0.35,
        pooled_ci_low=0.1,
        pooled_ci_high=0.6,
        metric_label="MD",
        log_scale=False,
        favours_left=None,
        favours_right=None,
        subgroup_summaries=None,
    )
    try:
        h_sub = fig_with_sub.get_size_inches()[1]
        h_plain = fig_plain.get_size_inches()[1]
        assert h_sub > h_plain
    finally:
        plt.close(fig_with_sub)
        plt.close(fig_plain)


def test_log_scale_draws_null_at_one():
    fig = _build_figure(
        rows=_rows(),
        pooled_estimate=0.0,
        pooled_ci_low=-0.5,
        pooled_ci_high=0.5,
        metric_label="Odds ratio",
        log_scale=True,
        favours_left=None,
        favours_right=None,
        subgroup_summaries=None,
    )
    try:
        ax = fig.axes[0]
        # When log_scale=True, the renderer should mark x=0 (i.e. log(1)) as null
        # The vertical reference line is at x=0 on the log-yi axis.
        # Verify the axis range includes 0.
        xmin, xmax = ax.get_xlim()
        assert xmin <= 0 <= xmax
    finally:
        plt.close(fig)


def test_no_matplotlib_state_leak_between_calls():
    for _ in range(10):
        render_forest_png(
            rows=_rows(),
            pooled_estimate=0.4,
            pooled_ci_low=0.1,
            pooled_ci_high=0.7,
            metric_label="MD",
            log_scale=False,
            favours_left=None,
            favours_right=None,
        )
    assert plt.get_fignums() == []
