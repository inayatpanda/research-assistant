"""Phase 13 (MP13) — Bootstrap distribution histogram with 95% CI bands."""
from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from ._base import fig_context, fig_to_data_uri


def render_bootstrap_distribution(
    *,
    distribution: Sequence[float],
    observed: float,
    ci_low: float,
    ci_high: float,
    title: str = "Bootstrap distribution",
) -> dict[str, Any]:
    arr = np.asarray(list(distribution), dtype=float)
    with fig_context() as fig:
        ax = fig.gca()
        ax.hist(arr, bins=40, color="#bac8ff", edgecolor="#4c6ef5")
        ax.axvline(observed, color="#fa5252", linewidth=2, label=f"Observed = {observed:.3g}")
        ax.axvline(ci_low, color="#495057", linestyle="--", linewidth=1, label="95% CI")
        ax.axvline(ci_high, color="#495057", linestyle="--", linewidth=1)
        ax.set_xlabel("Bootstrap statistic")
        ax.set_ylabel("Frequency")
        ax.set_title(title)
        ax.legend(loc="best", fontsize=8)
        return fig_to_data_uri(fig)
