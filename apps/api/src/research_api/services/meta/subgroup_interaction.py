"""Subgroup Q-between interaction test (Phase 19 / MP19).

Q_between = Q_total − Σ Q_within. df = (n_subgroups − 1). p computed
from a chi-square distribution with df degrees of freedom.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from scipy import stats

from .effect_sizes import Effect
from .heterogeneity import heterogeneity


@dataclass(frozen=True)
class SubgroupInteractionResult:
    q_between: float
    df: int
    p_interaction: float


def subgroup_q_between(
    effects_by_subgroup: Mapping[str, Sequence[Effect]],
) -> SubgroupInteractionResult:
    """Compute the Q-between interaction statistic.

    Only subgroups with ≥ 2 studies contribute Q_within (single-study
    subgroups have Q=0 by definition). Requires at least two non-empty
    subgroups; raises ``ValueError`` otherwise.
    """
    nonempty = {k: list(v) for k, v in effects_by_subgroup.items() if v}
    if len(nonempty) < 2:
        raise ValueError("subgroup_q_between needs at least 2 non-empty subgroups")

    all_effects: list[Effect] = []
    for v in nonempty.values():
        all_effects.extend(v)
    if len(all_effects) < 2:
        raise ValueError("subgroup_q_between needs at least 2 studies overall")

    q_total = heterogeneity(all_effects).q
    q_within = 0.0
    for studies in nonempty.values():
        if len(studies) >= 2:
            q_within += heterogeneity(studies).q
    q_between = max(0.0, q_total - q_within)
    df = len(nonempty) - 1
    p_interaction = float(1.0 - stats.chi2.cdf(q_between, df)) if df >= 1 else 1.0
    return SubgroupInteractionResult(
        q_between=float(q_between),
        df=int(df),
        p_interaction=float(p_interaction),
    )


__all__ = ["SubgroupInteractionResult", "subgroup_q_between"]
