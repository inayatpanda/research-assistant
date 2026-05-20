"""Phase 18 (MP18) — ICER + dominance + Net Monetary Benefit.

ICER quadrant interpretation (intervention vs comparator):

  * NW (dCost < 0, dQALY > 0) — *dominant*: cheaper AND more effective →
    obviously cost-effective. ICER undefined (we return None and
    dominance_status="dominant").
  * SE (dCost > 0, dQALY < 0) — *dominated*: more expensive AND less
    effective → obviously not cost-effective. ICER undefined (None,
    dominance_status="dominated").
  * NE (dCost > 0, dQALY > 0) — positive ICER, compare to WTP threshold.
    dominance_status="northeast" with ICER = dCost / dQALY.
  * SW (dCost < 0, dQALY < 0) — negative ICER, intervention cheaper but
    less effective (a "weak" trade-off; clinical context required).
    dominance_status="southwest" with ICER = dCost / dQALY (positive
    number magnitude-wise; interpretation flips: a HIGHER ICER means
    bigger savings per QALY lost).

The integer-quadrant tag is preferred over dominance_status="icer_calculated"
because consumers want to render different chips for NW/NE/SW/SE.
``"icer_calculated"`` is still emitted when both diffs are exactly zero
(degenerate — treated as a non-dominant equivalent).
"""
from __future__ import annotations

import math
from typing import Literal, TypedDict


DominanceStatus = Literal[
    "dominant", "dominated", "icer_calculated", "northeast", "southwest"
]


class ICERResult(TypedDict):
    icer: float | None
    dominance_status: DominanceStatus


def compute_icer(
    mean_cost_diff: float, mean_qaly_diff: float, *, eps: float = 1e-9
) -> ICERResult:
    """Compute ICER + quadrant-based dominance.

    Costs and QALYs are *intervention minus comparator*.

    ``eps`` is the magnitude below which a diff is treated as zero. This
    avoids division-by-zero crashes when bootstrap reps land on the
    horizontal/vertical axis. The default 1e-9 is conservative.
    """
    dC = float(mean_cost_diff)
    dQ = float(mean_qaly_diff)
    if abs(dC) < eps and abs(dQ) < eps:
        return {"icer": None, "dominance_status": "icer_calculated"}
    if dC < -eps and dQ > eps:
        return {"icer": None, "dominance_status": "dominant"}
    if dC > eps and dQ < -eps:
        return {"icer": None, "dominance_status": "dominated"}
    # NE (positive ICER) or SW (negative numerator + denominator → positive
    # numerically). Either way ICER = dC / dQ is well-defined.
    if abs(dQ) < eps:
        # On the vertical axis: intervention costs differ but QALYs equal.
        # Convention: report ICER as +/- inf with a quadrant tag based on dC.
        return {
            "icer": math.inf if dC > 0 else -math.inf,
            "dominance_status": "northeast" if dC > 0 else "southwest",
        }
    icer = dC / dQ
    if dC > 0 and dQ > 0:
        return {"icer": float(icer), "dominance_status": "northeast"}
    # dC < 0 and dQ < 0  → SW: numerically the ratio is positive (negative /
    # negative). Keep the sign so consumers can spot SW vs NE quickly.
    return {"icer": float(icer), "dominance_status": "southwest"}


def compute_nmb(
    mean_cost_diff: float, mean_qaly_diff: float, *, wtp_threshold: float
) -> float:
    """Net Monetary Benefit at a given willingness-to-pay threshold.

    NMB = wtp * dQALY - dCost. NMB > 0 → cost-effective at that WTP.
    """
    return float(wtp_threshold * float(mean_qaly_diff) - float(mean_cost_diff))


def nmb_at_thresholds(
    mean_cost_diff: float,
    mean_qaly_diff: float,
    *,
    thresholds: list[int] | list[float],
) -> dict[str, float]:
    """Convenience: compute NMB at each of a list of WTP thresholds.

    Returns ``{str(int(wtp)): nmb}`` for stable JSON keys.
    """
    out: dict[str, float] = {}
    for wtp in thresholds:
        out[str(int(wtp))] = compute_nmb(
            mean_cost_diff, mean_qaly_diff, wtp_threshold=float(wtp)
        )
    return out


__all__ = ["compute_icer", "compute_nmb", "nmb_at_thresholds", "ICERResult"]
