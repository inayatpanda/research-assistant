"""Backend init + figure helpers for stats chart rendering — Phase 8.5.

All chart renderers in this package import from here so the matplotlib
backend is pinned to 'Agg' (server-side, headless) exactly once.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
from io import BytesIO
from typing import Any, Iterator

import matplotlib

matplotlib.use("Agg")  # MUST come before any pyplot import.
import matplotlib.pyplot as plt  # noqa: E402
import seaborn as sns  # noqa: E402

_DPI = 130
_FIGSIZE = (6.5, 4.0)

# Apply a consistent seaborn theme once at import time.
sns.set_theme(style="whitegrid", context="notebook")


@contextmanager
def fig_context(figsize: tuple[float, float] = _FIGSIZE) -> Iterator[Any]:
    """Yield a matplotlib Figure that is guaranteed to be closed on exit."""
    fig = plt.figure(figsize=figsize, dpi=_DPI)
    try:
        yield fig
    finally:
        plt.close(fig)


def fig_to_png_bytes(fig: Any) -> bytes:
    """Render a Figure to PNG bytes (no temp file, no disk I/O)."""
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=_DPI, bbox_inches="tight")
    buf.seek(0)
    return buf.read()


def fig_to_data_uri(fig: Any) -> dict[str, Any]:
    """Render a Figure to the storage dict shape expected by AnalysisResult.chart."""
    raw = fig_to_png_bytes(fig)
    return {
        "format": "png",
        "data_uri": "data:image/png;base64," + base64.b64encode(raw).decode("ascii"),
        "byte_size": len(raw),
    }
