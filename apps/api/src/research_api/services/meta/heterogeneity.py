"""Heterogeneity statistics: Cochran Q, I^2, tau^2 (DerSimonian-Laird)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from scipy import stats

from .effect_sizes import Effect


@dataclass(frozen=True)
class Heterogeneity:
    q: float
    df: int
    p: float
    i2: float       # 0–100, percent
    tau2: float


def heterogeneity(effects: Sequence[Effect]) -> Heterogeneity:
    """Compute Q, df, p, I^2, and DL tau^2 from a sequence of per-study effects."""
    if len(effects) < 2:
        raise ValueError("heterogeneity needs at least 2 effects")
    weights: list[float] = []
    for e in effects:
        if e.vi <= 0:
            raise ValueError("heterogeneity: all variances must be positive")
        weights.append(1.0 / e.vi)
    sum_w = sum(weights)
    sum_wy = sum(w * e.yi for w, e in zip(weights, effects))
    yi_fixed = sum_wy / sum_w
    q = sum(w * (e.yi - yi_fixed) ** 2 for w, e in zip(weights, effects))
    df = len(effects) - 1
    p = float(1.0 - stats.chi2.cdf(q, df)) if df >= 1 else 1.0
    i2 = 100.0 * max(0.0, (q - df) / q) if q > 0 else 0.0
    # DerSimonian-Laird tau^2 = max(0, (Q - df) / (sum_w - sum_w_sq/sum_w))
    sum_w_sq = sum(w * w for w in weights)
    denom = sum_w - sum_w_sq / sum_w
    if denom <= 0:
        tau2 = 0.0
    else:
        tau2 = max(0.0, (q - df) / denom)
    return Heterogeneity(
        q=float(q),
        df=int(df),
        p=float(p),
        i2=float(i2),
        tau2=float(tau2),
    )
