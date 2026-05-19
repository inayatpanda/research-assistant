"""Phase 13 (MP13) — Permutation null-distribution histogram."""
from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from ._base import fig_context, fig_to_data_uri


def render_permutation_distribution(
    *,
    null_distribution: Sequence[float],
    observed: float,
    title: str = "Permutation null distribution",
) -> dict[str, Any]:
    arr = np.asarray(list(null_distribution), dtype=float)
    with fig_context() as fig:
        ax = fig.gca()
        ax.hist(arr, bins=40, color="#dee2e6", edgecolor="#868e96")
        ax.axvline(
            observed,
            color="#fa5252",
            linewidth=2,
            label=f"Observed = {observed:.3g}",
        )
        ax.set_xlabel("Statistic under H0 (label exchange)")
        ax.set_ylabel("Frequency")
        ax.set_title(title)
        ax.legend(loc="best", fontsize=8)
        return fig_to_data_uri(fig)
