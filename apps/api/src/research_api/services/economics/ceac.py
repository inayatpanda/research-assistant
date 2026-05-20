"""Phase 18 (MP18) — Cost-Effectiveness Acceptability Curve (CEAC).

For each WTP threshold, the CEAC reports the fraction of bootstrap reps
where Net Monetary Benefit (NMB = wtp*dQALY - dCost) is positive — i.e. the
probability that the intervention is cost-effective at that WTP.

Implementation: pure NumPy. Bootstrap rep list is a sequence of dicts
``{dCost, dQALY}`` (as produced by ``cost_qaly_regression.bivariate_bootstrap``).
"""
from __future__ import annotations

from typing import Iterable, Sequence

import numpy as np


def build_ceac(
    plane_bootstrap: Sequence[dict[str, float]],
    *,
    wtp_range: tuple[int, int, int] = (0, 100_000, 1_000),
) -> list[dict[str, float]]:
    """Build a CEAC from a bootstrapped cost-effectiveness plane.

    Parameters
    ----------
    plane_bootstrap
        List of dicts with keys ``dCost`` and ``dQALY``.
    wtp_range
        ``(start, stop_inclusive, step)`` defining the grid of WTP values
        to evaluate. Defaults to 0..100,000 in 1,000 steps → 101 points.

    Returns
    -------
    List of ``{wtp, prob_costeffective}`` sorted ascending by WTP.
    """
    if not plane_bootstrap:
        return []
    start, stop, step = wtp_range
    if step <= 0:
        raise ValueError("wtp_range step must be positive")
    if stop < start:
        raise ValueError("wtp_range stop must be >= start")

    dC = np.fromiter((float(r["dCost"]) for r in plane_bootstrap), dtype=float)
    dQ = np.fromiter((float(r["dQALY"]) for r in plane_bootstrap), dtype=float)
    n = len(dC)
    if n == 0:
        return []

    out: list[dict[str, float]] = []
    wtp = start
    while wtp <= stop:
        nmb = float(wtp) * dQ - dC
        prob = float((nmb > 0).sum()) / n
        out.append({"wtp": float(wtp), "prob_costeffective": prob})
        wtp += step
    return out


__all__ = ["build_ceac"]
