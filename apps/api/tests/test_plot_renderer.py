"""Phase 13.5 (MP13.5) — plot_renderer tests."""
import pandas as pd
import pytest

from research_api.services.stats.plot_renderer import (
    PlotRenderError,
    VALID_GEOMS,
    render_plot,
)


@pytest.fixture
def df() -> pd.DataFrame:
    return pd.DataFrame({
        "x": [1, 2, 3, 4, 5, 6, 7, 8],
        "y": [2.1, 1.9, 2.8, 3.0, 4.2, 4.1, 5.1, 5.5],
        "g": ["a", "a", "b", "b", "a", "b", "a", "b"],
        "v": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
    })


def _png(b: bytes) -> bool:
    return b[:4] == b"\x89PNG"


def test_render_point_returns_png(df):
    out = render_plot(df, {"geom": "point", "x": "x", "y": "y"})
    assert _png(out)


def test_render_bar_count_only_returns_png(df):
    out = render_plot(df, {"geom": "bar", "x": "g"})
    assert _png(out)


def test_render_box_returns_png(df):
    out = render_plot(df, {"geom": "box", "x": "g", "y": "y"})
    assert _png(out)


def test_render_violin_returns_png(df):
    out = render_plot(df, {"geom": "violin", "x": "g", "y": "y"})
    assert _png(out)


def test_render_histogram_returns_png(df):
    out = render_plot(df, {"geom": "histogram", "x": "y"})
    assert _png(out)


def test_render_density_returns_png(df):
    out = render_plot(df, {"geom": "density", "x": "y"})
    assert _png(out)


def test_render_line_returns_png(df):
    out = render_plot(df, {"geom": "line", "x": "x", "y": "y"})
    assert _png(out)


def test_render_heatmap_requires_value(df):
    with pytest.raises(PlotRenderError, match="value"):
        render_plot(df, {"geom": "heatmap", "x": "x", "y": "g"})


def test_render_heatmap_works():
    df = pd.DataFrame({
        "row": ["a", "a", "b", "b", "c", "c"],
        "col": ["x", "y", "x", "y", "x", "y"],
        "v": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
    })
    out = render_plot(
        df, {"geom": "heatmap", "x": "col", "y": "row", "args": {"value": "v"}}
    )
    assert _png(out)


def test_render_pair_requires_columns(df):
    with pytest.raises(PlotRenderError, match="columns"):
        render_plot(df, {"geom": "pair", "args": {}})


def test_render_pair_works(df):
    out = render_plot(df, {"geom": "pair", "args": {"columns": ["x", "y"]}})
    assert _png(out)


def test_unknown_geom_raises(df):
    with pytest.raises(PlotRenderError, match="unknown"):
        render_plot(df, {"geom": "nope", "x": "x"})


def test_missing_x_raises(df):
    with pytest.raises(PlotRenderError, match="requires"):
        render_plot(df, {"geom": "point", "y": "y"})


def test_missing_column_raises(df):
    with pytest.raises(PlotRenderError, match="not in"):
        render_plot(df, {"geom": "point", "x": "nope", "y": "y"})


def test_invalid_column_name_raises(df):
    with pytest.raises(PlotRenderError, match="invalid"):
        render_plot(df, {"geom": "point", "x": "1bad", "y": "y"})


def test_color_facet_path(df):
    out = render_plot(
        df,
        {"geom": "point", "x": "x", "y": "y", "color": "g", "facet": "g"},
    )
    assert _png(out)


def test_valid_geoms_contains_expected():
    assert "point" in VALID_GEOMS
    assert "bar" in VALID_GEOMS
    assert "heatmap" in VALID_GEOMS
    assert "pair" in VALID_GEOMS
