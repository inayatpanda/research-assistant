"""Phase 18 (MP18) — Economic chart renderers (CE plane, CEAC, tornado).

All return PNG bytes via matplotlib's headless Agg backend, mirroring the
existing `services/stats/charts/*.py` and `services/meta/forest_plot.py`
patterns.
"""
from __future__ import annotations

import base64
from io import BytesIO
from typing import Sequence

import matplotlib

matplotlib.use("Agg")  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402


_DPI = 130
_FIGSIZE = (6.5, 5.0)


def _fig_to_png(fig) -> bytes:  # type: ignore[no-untyped-def]
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=_DPI, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def png_to_data_uri(png: bytes) -> str:
    """Encode raw PNG bytes as a ``data:image/png;base64,...`` URI."""
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def render_ce_plane(
    plane_bootstrap: Sequence[dict[str, float]],
    *,
    wtp_thresholds: Sequence[int] | None = None,
    intervention_label: str = "Intervention",
    comparator_label: str = "Comparator",
    currency: str = "GBP",
) -> bytes:
    """Cost-effectiveness plane.

    Scatter of bootstrap (dQALY, dCost) — Q on x, C on y — with the four
    quadrants labelled and WTP threshold lines drawn through the origin
    at slope = wtp (cost per QALY).
    """
    fig, ax = plt.subplots(figsize=_FIGSIZE, dpi=_DPI)
    if plane_bootstrap:
        qs = [float(r["dQALY"]) for r in plane_bootstrap]
        cs = [float(r["dCost"]) for r in plane_bootstrap]
        ax.scatter(qs, cs, alpha=0.35, s=14, color="#3b82f6", edgecolor="none")

    ax.axhline(0.0, color="#374151", linewidth=0.9, alpha=0.7)
    ax.axvline(0.0, color="#374151", linewidth=0.9, alpha=0.7)

    # WTP threshold lines through the origin: c = wtp * q.
    if wtp_thresholds:
        x_lim = ax.get_xlim()
        max_q = max(abs(x_lim[0]), abs(x_lim[1]), 0.05)
        for wtp in wtp_thresholds:
            ax.plot(
                [-max_q, max_q],
                [-float(wtp) * max_q, float(wtp) * max_q],
                color="#f59e0b",
                linewidth=1.0,
                linestyle="--",
                alpha=0.8,
                label=f"WTP {currency} {int(wtp):,}/QALY",
            )

    ax.set_xlabel(
        f"Incremental QALYs ({intervention_label} − {comparator_label})"
    )
    ax.set_ylabel(f"Incremental cost ({currency})")
    ax.set_title("Cost-effectiveness plane")
    if wtp_thresholds:
        ax.legend(loc="best", fontsize=8, framealpha=0.85)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return _fig_to_png(fig)


def render_ceac(
    ceac_data: Sequence[dict[str, float]],
    *,
    wtp_thresholds: Sequence[int] | None = None,
    intervention_label: str = "Intervention",
    currency: str = "GBP",
) -> bytes:
    """Probability the intervention is cost-effective vs WTP."""
    fig, ax = plt.subplots(figsize=_FIGSIZE, dpi=_DPI)
    if ceac_data:
        xs = [float(p["wtp"]) for p in ceac_data]
        ys = [float(p["prob_costeffective"]) for p in ceac_data]
        ax.plot(xs, ys, linewidth=2.0, color="#10b981")

    if wtp_thresholds:
        for wtp in wtp_thresholds:
            ax.axvline(
                float(wtp),
                color="#f59e0b",
                linewidth=0.9,
                linestyle="--",
                alpha=0.8,
            )

    ax.set_xlabel(f"Willingness-to-pay ({currency} per QALY)")
    ax.set_ylabel(f"P({intervention_label} cost-effective)")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title("Cost-effectiveness acceptability curve")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return _fig_to_png(fig)


def render_tornado(
    dsa_results: Sequence[dict[str, float | str]],
    *,
    metric_label: str = "ICER",
    base_value: float | None = None,
) -> bytes:
    """One-way deterministic sensitivity analysis tornado.

    Expects each entry to carry ``param``, ``low_icer``, ``high_icer``
    (or equivalents named differently — caller can map). The bars are
    sorted by absolute width descending.
    """
    fig, ax = plt.subplots(figsize=_FIGSIZE, dpi=_DPI)
    rows = []
    for r in dsa_results:
        try:
            low = float(r["low_icer"])  # type: ignore[arg-type]
            high = float(r["high_icer"])  # type: ignore[arg-type]
            name = str(r["param"])
        except (KeyError, TypeError, ValueError):
            continue
        if low > high:
            low, high = high, low
        rows.append((name, low, high))
    rows.sort(key=lambda x: abs(x[2] - x[1]), reverse=True)

    if not rows:
        ax.text(0.5, 0.5, "(no DSA results)", ha="center", va="center")
    else:
        names = [r[0] for r in rows]
        lows = [r[1] for r in rows]
        highs = [r[2] for r in rows]
        y = list(range(len(rows)))
        baseline = float(base_value) if base_value is not None else (sum(lows + highs) / (2 * len(rows)))
        for yi, lo, hi in zip(y, lows, highs):
            ax.barh(yi, hi - lo, left=lo, height=0.6, color="#6366f1", alpha=0.75)
            ax.plot([baseline, baseline], [yi - 0.4, yi + 0.4], color="#374151")
        ax.set_yticks(y)
        ax.set_yticklabels(names)
        ax.invert_yaxis()
        ax.axvline(baseline, color="#374151", linewidth=0.9)
        ax.set_xlabel(metric_label)
    ax.set_title("One-way deterministic sensitivity analysis")
    ax.grid(True, alpha=0.25, axis="x")
    fig.tight_layout()
    return _fig_to_png(fig)


__all__ = [
    "render_ce_plane",
    "render_ceac",
    "render_tornado",
    "png_to_data_uri",
]
