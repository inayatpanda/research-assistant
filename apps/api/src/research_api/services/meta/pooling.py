"""Pooling: inverse-variance fixed-effects + DerSimonian-Laird random-effects."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from scipy import stats

from .effect_sizes import Effect
from .heterogeneity import heterogeneity

_Z975 = 1.959964


@dataclass(frozen=True)
class PooledResult:
    estimate: float
    se: float
    ci_low: float
    ci_high: float
    z: float
    p: float
    weights: list[float]  # normalised, sum to 1
    model: str


def _validate(effects: Sequence[Effect]) -> None:
    if len(effects) < 2:
        raise ValueError("pooling requires at least 2 studies")
    for e in effects:
        if e.vi <= 0:
            raise ValueError("pooling: all variances must be positive")


def pool_fixed(effects: Sequence[Effect]) -> PooledResult:
    """Inverse-variance fixed-effects pooling."""
    _validate(effects)
    raw_w = [1.0 / e.vi for e in effects]
    sum_w = sum(raw_w)
    yi_bar = sum(w * e.yi for w, e in zip(raw_w, effects)) / sum_w
    vi_bar = 1.0 / sum_w
    se = math.sqrt(vi_bar)
    ci_low = yi_bar - _Z975 * se
    ci_high = yi_bar + _Z975 * se
    z = yi_bar / se if se > 0 else 0.0
    p = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))
    norm_w = [w / sum_w for w in raw_w]
    return PooledResult(
        estimate=float(yi_bar),
        se=float(se),
        ci_low=float(ci_low),
        ci_high=float(ci_high),
        z=float(z),
        p=p,
        weights=norm_w,
        model="fixed",
    )


def pool_random_dl(effects: Sequence[Effect]) -> PooledResult:
    """Random-effects (DerSimonian-Laird) pooling."""
    _validate(effects)
    het = heterogeneity(effects)
    tau2 = het.tau2
    raw_w = [1.0 / (e.vi + tau2) for e in effects]
    sum_w = sum(raw_w)
    yi_bar = sum(w * e.yi for w, e in zip(raw_w, effects)) / sum_w
    vi_bar = 1.0 / sum_w
    se = math.sqrt(vi_bar)
    ci_low = yi_bar - _Z975 * se
    ci_high = yi_bar + _Z975 * se
    z = yi_bar / se if se > 0 else 0.0
    p = float(2.0 * (1.0 - stats.norm.cdf(abs(z))))
    norm_w = [w / sum_w for w in raw_w]
    return PooledResult(
        estimate=float(yi_bar),
        se=float(se),
        ci_low=float(ci_low),
        ci_high=float(ci_high),
        z=float(z),
        p=p,
        weights=norm_w,
        model="random",
    )


def pool(effects: Sequence[Effect], model: str) -> PooledResult:
    if model == "fixed":
        return pool_fixed(effects)
    if model == "random":
        return pool_random_dl(effects)
    raise ValueError(f"unknown pooling model {model!r}")
