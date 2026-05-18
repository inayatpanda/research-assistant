"""CONSORT 2010 flow counter — pure functions.

derive_flow() turns a ConsortData payload into a ConsortFlow ready for the
SVG renderer, computing arithmetic warnings as it goes. Warnings are advisory
— the renderer still draws whatever numbers the user has entered.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConsortFlow:
    assessed: int | None
    excluded: int | None
    excluded_reasons: dict[str, int] | None
    randomised: int | None
    allocated: dict[str, int | None]
    received: dict[str, int | None]
    lost_followup: dict[str, int | None]
    discontinued: dict[str, int | None]
    analysed: dict[str, int | None]
    warnings: list[str]


def _g(d: Any, name: str) -> int | None:
    """Tolerant getter — supports either a dict or a pydantic / ORM object."""
    if isinstance(d, dict):
        v = d.get(name)
    else:
        v = getattr(d, name, None)
    return None if v is None else int(v)


def _gd(d: Any, name: str) -> dict[str, int] | None:
    if isinstance(d, dict):
        v = d.get(name)
    else:
        v = getattr(d, name, None)
    if v is None:
        return None
    return {str(k): int(n) for k, n in v.items()}


def derive_flow(data: Any) -> ConsortFlow:
    assessed = _g(data, "enrollment_assessed")
    excluded = _g(data, "enrollment_excluded")
    reasons = _gd(data, "enrollment_excluded_reasons")
    randomised = _g(data, "randomised")
    a_i = _g(data, "allocated_intervention")
    a_c = _g(data, "allocated_control")
    r_i = _g(data, "intervention_received")
    r_c = _g(data, "control_received")
    lf_i = _g(data, "intervention_lost_followup")
    lf_c = _g(data, "control_lost_followup")
    dc_i = _g(data, "intervention_discontinued")
    dc_c = _g(data, "control_discontinued")
    an_i = _g(data, "intervention_analysed")
    an_c = _g(data, "control_analysed")

    warnings: list[str] = []

    if reasons and excluded is not None:
        rsum = sum(reasons.values())
        if rsum != excluded:
            warnings.append(
                f"Sum of exclusion reasons ({rsum}) does not match "
                f"enrollment_excluded ({excluded})."
            )

    if assessed is not None and excluded is not None and randomised is not None:
        if assessed - excluded != randomised:
            warnings.append(
                f"assessed - excluded ({assessed - excluded}) does not match "
                f"randomised ({randomised})."
            )

    if a_i is not None and a_c is not None and randomised is not None:
        if a_i + a_c != randomised:
            warnings.append(
                f"allocated_intervention + allocated_control ({a_i + a_c}) does "
                f"not match randomised ({randomised})."
            )

    if a_i is not None and r_i is not None and r_i > a_i:
        warnings.append(
            f"intervention_received ({r_i}) exceeds allocated_intervention ({a_i})."
        )
    if a_c is not None and r_c is not None and r_c > a_c:
        warnings.append(
            f"control_received ({r_c}) exceeds allocated_control ({a_c})."
        )

    return ConsortFlow(
        assessed=assessed,
        excluded=excluded,
        excluded_reasons=reasons,
        randomised=randomised,
        allocated={"intervention": a_i, "control": a_c},
        received={"intervention": r_i, "control": r_c},
        lost_followup={"intervention": lf_i, "control": lf_c},
        discontinued={"intervention": dc_i, "control": dc_c},
        analysed={"intervention": an_i, "control": an_c},
        warnings=warnings,
    )
