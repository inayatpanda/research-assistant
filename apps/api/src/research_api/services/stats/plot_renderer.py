"""Phase 13.5 (MP13.5) — Pure-function plot renderer.

Given a DataFrame and a spec dict ``{geom, x, y?, color?, facet?, args?}``,
returns PNG bytes via seaborn / matplotlib. Headless backend pinned in
``charts._base``.
"""
from __future__ import annotations

import re
from typing import Any

import pandas as pd
import seaborn as sns

from .charts._base import fig_context, fig_to_png_bytes

_COL_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

VALID_GEOMS = {
    "point",
    "bar",
    "line",
    "box",
    "violin",
    "heatmap",
    "histogram",
    "density",
    "pair",
}


class PlotRenderError(ValueError):
    """Raised when a spec is structurally invalid for the supplied dataframe."""


def _check_col(name: Any) -> str:
    if not isinstance(name, str) or not _COL_RE.match(name):
        raise PlotRenderError(f"invalid column name {name!r}")
    return name


def _require(df: pd.DataFrame, cols: list[str]) -> None:
    missing = [c for c in cols if c and c not in df.columns]
    if missing:
        raise PlotRenderError(f"columns not in dataframe: {missing!r}")


def _facet_grid_render(
    df: pd.DataFrame,
    geom: str,
    x: str | None,
    y: str | None,
    color: str | None,
    facet: str | None,
    args: dict[str, Any],
) -> bytes:
    """Use seaborn FacetGrid for the geoms that map cleanly onto it.

    Caller has already validated columns.
    """
    g = sns.FacetGrid(df, col=facet, hue=color, height=3.2, aspect=1.3)
    if geom == "point":
        g.map_dataframe(sns.scatterplot, x=x, y=y)
    elif geom == "line":
        g.map_dataframe(sns.lineplot, x=x, y=y)
    elif geom == "histogram":
        g.map_dataframe(sns.histplot, x=x, kde=False)
    elif geom == "density":
        g.map_dataframe(sns.kdeplot, x=x, fill=True)
    elif geom == "box":
        g.map_dataframe(sns.boxplot, x=x, y=y)
    elif geom == "violin":
        g.map_dataframe(sns.violinplot, x=x, y=y)
    elif geom == "bar":
        if y is None:
            # Count plot via histplot of categorical
            g.map_dataframe(sns.countplot, x=x)
        else:
            g.map_dataframe(sns.barplot, x=x, y=y)
    else:  # pragma: no cover - guarded by caller
        raise PlotRenderError(f"FacetGrid not supported for geom={geom!r}")
    if color is not None:
        g.add_legend()
    fig = g.figure
    out = fig_to_png_bytes(fig)
    import matplotlib.pyplot as plt
    plt.close(fig)
    return out


def render_plot(df: pd.DataFrame, spec: dict[str, Any]) -> bytes:
    """Render a single plot spec to PNG bytes.

    Raises PlotRenderError on structural problems (unknown geom, missing
    column). Never raises matplotlib / seaborn exceptions out — they are
    wrapped as PlotRenderError too.
    """
    if not isinstance(spec, dict):
        raise PlotRenderError("spec must be a dict")
    geom = spec.get("geom")
    if geom not in VALID_GEOMS:
        raise PlotRenderError(f"unknown geom {geom!r}")
    x = spec.get("x")
    y = spec.get("y")
    color = spec.get("color")
    facet = spec.get("facet")
    args = spec.get("args") or {}
    if x is not None:
        _check_col(x)
    if y is not None:
        _check_col(y)
    if color is not None:
        _check_col(color)
    if facet is not None:
        _check_col(facet)

    needed: list[str] = []
    if geom not in {"pair"} and x is not None:
        needed.append(x)
    if y is not None:
        needed.append(y)
    if color is not None:
        needed.append(color)
    if facet is not None:
        needed.append(facet)
    _require(df, needed)

    # Geom-specific channel requirements
    if geom in {"point", "line", "box", "violin"}:
        if not x or not y:
            raise PlotRenderError(f"geom={geom!r} requires both x and y")
    elif geom in {"histogram", "density"}:
        if not x:
            raise PlotRenderError(f"geom={geom!r} requires x")
    elif geom == "bar":
        if not x:
            raise PlotRenderError("geom=bar requires x")
    elif geom == "heatmap":
        value_col = args.get("value")
        if not x or not y or not value_col:
            raise PlotRenderError("geom=heatmap requires x, y, and args.value")
        _check_col(value_col)
        _require(df, [value_col])
    elif geom == "pair":
        cols = args.get("columns")
        if not isinstance(cols, list) or len(cols) < 2:
            raise PlotRenderError(
                "geom=pair requires args.columns (list of >=2 numeric columns)"
            )
        for c in cols:
            _check_col(c)
        _require(df, cols)

    try:
        # FacetGrid path for facetted plots
        if facet is not None and geom in {
            "point",
            "line",
            "histogram",
            "density",
            "box",
            "violin",
            "bar",
        }:
            return _facet_grid_render(df, geom, x, y, color, facet, args)

        # Pair plot path
        if geom == "pair":
            cols = list(args["columns"])  # validated above
            g = sns.pairplot(df[cols].dropna(), hue=color)
            fig = g.figure
            out = fig_to_png_bytes(fig)
            import matplotlib.pyplot as plt
            plt.close(fig)
            return out

        # Single-axes geoms
        with fig_context() as fig:
            ax = fig.add_subplot(1, 1, 1)
            if geom == "point":
                sns.scatterplot(data=df, x=x, y=y, hue=color, ax=ax)
            elif geom == "line":
                sns.lineplot(data=df, x=x, y=y, hue=color, ax=ax)
            elif geom == "bar":
                if y is None:
                    sns.countplot(data=df, x=x, hue=color, ax=ax)
                else:
                    sns.barplot(data=df, x=x, y=y, hue=color, ax=ax)
            elif geom == "box":
                sns.boxplot(data=df, x=x, y=y, hue=color, ax=ax)
            elif geom == "violin":
                sns.violinplot(data=df, x=x, y=y, hue=color, ax=ax)
            elif geom == "histogram":
                sns.histplot(data=df, x=x, hue=color, kde=False, ax=ax)
            elif geom == "density":
                sns.kdeplot(data=df, x=x, hue=color, fill=True, ax=ax)
            elif geom == "heatmap":
                value_col = args["value"]
                pivot = df.pivot_table(
                    index=y,
                    columns=x,
                    values=value_col,
                    aggfunc=args.get("agg", "mean"),
                )
                sns.heatmap(pivot, ax=ax, annot=args.get("annot", False), cmap="viridis")
            ax.set_xlabel(x or "")
            ax.set_ylabel(y or "")
            title = args.get("title")
            if isinstance(title, str) and title:
                ax.set_title(title)
            return fig_to_png_bytes(fig)
    except PlotRenderError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise PlotRenderError(f"plot render failed: {exc}") from exc
