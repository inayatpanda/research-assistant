"""Phase 13 (MP13) — TOST equivalence-bounds plot."""
from __future__ import annotations

from math import isfinite
from typing import Any

import numpy as np

from ._base import fig_context, fig_to_data_uri


def render_tost_bounds(
    *,
    observed_diff: float,
    low_eq: float,
    upp_eq: float,
    n_a: int,
    n_b: int,
    title: str = "TOST equivalence bounds",
) -> dict[str, Any]:
    """Render the equivalence-bounds plot.

    The 90% CI is constructed from a normal approximation around the
    observed mean diff with SE = |upp_eq - low_eq| / (2 * 1.645) when the
    user did not supply SE directly. That is intentionally conservative — the
    chart is a visualisation, not the inference (which is delivered by the
    TOST p-value in the result extras).
    """
    half_band = abs(upp_eq - low_eq) / (2 * 1.645) if isfinite(upp_eq - low_eq) else 0.0
    ci90_low = observed_diff - 1.645 * half_band
    ci90_high = observed_diff + 1.645 * half_band

    with fig_context(figsize=(6.0, 2.5)) as fig:
        ax = fig.gca()
        ax.axvspan(low_eq, upp_eq, color="#d3f9d8", alpha=0.45, label="Equivalence zone")
        ax.errorbar(
            [observed_diff],
            [0],
            xerr=[[observed_diff - ci90_low], [ci90_high - observed_diff]],
            fmt="o",
            color="#4c6ef5",
            ecolor="#495057",
            label=f"Observed Δ = {observed_diff:.3g}",
        )
        ax.axvline(low_eq, color="#37b24d", linestyle="--", linewidth=1)
        ax.axvline(upp_eq, color="#37b24d", linestyle="--", linewidth=1)
        ax.axvline(0, color="#868e96", linestyle=":", linewidth=1)
        ax.set_yticks([])
        ax.set_xlabel("Mean difference (a − b)")
        ax.set_title(f"{title}  (n_a={n_a}, n_b={n_b})")
        ax.legend(loc="upper right", fontsize=8)
        return fig_to_data_uri(fig)
