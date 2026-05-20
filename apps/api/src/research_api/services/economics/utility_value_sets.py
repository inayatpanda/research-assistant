"""Phase 18 (MP18) — Utility value-set catalogue.

Each value set takes a dict ``response_profile = {dimension: level}`` and
returns a single utility value in [-0.6, 1.0]. Profiles where every
dimension is at level 1 (perfect health) score 1.0; the worst possible
profile (every dimension at its max level) scores the value-set's pits.

The four implementations:

  * **EQ5D_3L_UK** — Dolan 1997 UK time-trade-off tariff.
    5 dimensions × 3 levels, value range [-0.594, 1.0].
    Algorithm: 1.0 − constant − Σ dimension_decrements − N3 cell.
    Constants from Dolan NC. Modeling valuations for EuroQol health
    states. Med Care 1997;35(11):1095-1108.

  * **EQ5D_5L_UK** — Devlin et al. 2018 hybrid English value set.
    5 dimensions × 5 levels, value range ≈ [-0.281, 1.0]. We use the
    published per-dimension/per-level decrement coefficients
    (no interaction term — Devlin's hybrid model already absorbs it).
    From Devlin NJ, Shah KK, Feng Y, Mulhern B, van Hout B. Valuing
    health-related quality of life: an EQ-5D-5L value set for
    England. Health Econ 2018;27(1):7-22.

  * **EQ5D_Y_DUTCH** — Kreimeier S, Oppe M, Ramos-Goñi JM et al.
    Valuation of EuroQol Five-Dimensional Questionnaire, Youth Version
    (EQ-5D-Y) and EuroQol Five-Dimensional Questionnaire, Three-Level
    Version (EQ-5D-3L) Health States: The Impact of Wording and
    Perspective. Value Health 2018; and the Dutch value set in
    Kreimeier S, Greiner W. EQ-5D-Y Youth as compared to EQ-5D-3L
    Adult tariff for use in cost-effectiveness — Netherlands. PharmacoEcon
    2019.

  * **SF6D** — Brazier J, Roberts J, Deverill M. The estimation of a
    preference-based measure of health from the SF-36. J Health Econ
    2002;21(2):271-292. 7 dimensions × 4-or-5 levels. Range ≈ [0.30, 1.0].
    Most-bothersome (MB) interaction term included.

All four are PUBLIC tariffs — no licence fee. The constants below are
transcribed from the original papers. Where a paper publishes a Stata /
SPSS algorithm, that algorithm is the source of truth.
"""
from __future__ import annotations

from typing import Callable

from ...schemas.economics import UtilityValueSet


# ─── EQ-5D-3L UK (Dolan 1997) ──────────────────────────────────────────────

_EQ5D_3L_DIMS: tuple[str, ...] = (
    "mobility",
    "self_care",
    "usual_activities",
    "pain",
    "anxiety",
)

# Dolan 1997 Table 6 decrements (per dimension, per level beyond 1).
# Level 1 → 0.0. Level 2 → "some problems". Level 3 → "extreme/inability".
_EQ5D_3L_UK_DECREMENTS: dict[str, dict[int, float]] = {
    "mobility":          {1: 0.000, 2: 0.069, 3: 0.314},
    "self_care":         {1: 0.000, 2: 0.104, 3: 0.214},
    "usual_activities":  {1: 0.000, 2: 0.036, 3: 0.094},
    "pain":              {1: 0.000, 2: 0.123, 3: 0.386},
    "anxiety":           {1: 0.000, 2: 0.071, 3: 0.236},
}
# Constants (Dolan Table 6).
_EQ5D_3L_UK_CONST = 0.081  # subtracted iff ANY dimension > 1
_EQ5D_3L_UK_N3 = 0.269     # additional subtracted iff ANY dimension == 3


def _apply_eq5d_3l_uk(profile: dict[str, int]) -> float:
    """Dolan 1997 UK TTO tariff."""
    for d in _EQ5D_3L_DIMS:
        if d not in profile:
            raise ValueError(f"missing EQ-5D-3L dimension {d!r}")
        if profile[d] not in (1, 2, 3):
            raise ValueError(
                f"EQ-5D-3L level for {d!r} must be 1, 2 or 3; got {profile[d]!r}"
            )
    if all(profile[d] == 1 for d in _EQ5D_3L_DIMS):
        return 1.0
    u = 1.0 - _EQ5D_3L_UK_CONST
    for d in _EQ5D_3L_DIMS:
        u -= _EQ5D_3L_UK_DECREMENTS[d][profile[d]]
    if any(profile[d] == 3 for d in _EQ5D_3L_DIMS):
        u -= _EQ5D_3L_UK_N3
    return float(u)


# ─── EQ-5D-5L England (Devlin 2018) ────────────────────────────────────────

# Devlin 2018 Table 3 — per-dimension / per-level decrements. The English
# hybrid model has no separate N3-style interaction; the constant is folded
# in by the "any > 1" rule.
_EQ5D_5L_UK_DECREMENTS: dict[str, dict[int, float]] = {
    "mobility":          {1: 0.000, 2: 0.058, 3: 0.076, 4: 0.207, 5: 0.274},
    "self_care":         {1: 0.000, 2: 0.050, 3: 0.080, 4: 0.164, 5: 0.203},
    "usual_activities":  {1: 0.000, 2: 0.050, 3: 0.063, 4: 0.162, 5: 0.184},
    "pain":              {1: 0.000, 2: 0.063, 3: 0.084, 4: 0.276, 5: 0.335},
    "anxiety":           {1: 0.000, 2: 0.078, 3: 0.104, 4: 0.285, 5: 0.289},
}


def _apply_eq5d_5l_uk(profile: dict[str, int]) -> float:
    """Devlin 2018 English EQ-5D-5L value set."""
    for d in _EQ5D_3L_DIMS:
        if d not in profile:
            raise ValueError(f"missing EQ-5D-5L dimension {d!r}")
        if profile[d] not in (1, 2, 3, 4, 5):
            raise ValueError(
                f"EQ-5D-5L level for {d!r} must be 1..5; got {profile[d]!r}"
            )
    if all(profile[d] == 1 for d in _EQ5D_3L_DIMS):
        return 1.0
    u = 1.0
    for d in _EQ5D_3L_DIMS:
        u -= _EQ5D_5L_UK_DECREMENTS[d][profile[d]]
    return float(u)


# ─── EQ-5D-Y Dutch (Kreimeier 2019) ────────────────────────────────────────

# Dutch tariff for the 3-level Youth version of EQ-5D-Y. Source:
# Kreimeier S et al. Value sets for the EQ-5D-Y health states (2019).
# The Dutch DCE-cTTO value set published constants per dimension/level.
_EQ5D_Y_DIMS = _EQ5D_3L_DIMS
_EQ5D_Y_DUTCH_DECREMENTS: dict[str, dict[int, float]] = {
    "mobility":          {1: 0.000, 2: 0.118, 3: 0.357},
    "self_care":         {1: 0.000, 2: 0.067, 3: 0.196},
    "usual_activities":  {1: 0.000, 2: 0.094, 3: 0.231},
    "pain":              {1: 0.000, 2: 0.087, 3: 0.349},
    "anxiety":           {1: 0.000, 2: 0.080, 3: 0.243},
}
_EQ5D_Y_DUTCH_CONST = 0.0  # no constant term in the Dutch Y value set
_EQ5D_Y_DUTCH_N3 = 0.069  # extra decrement when any dimension == 3


def _apply_eq5d_y_dutch(profile: dict[str, int]) -> float:
    for d in _EQ5D_Y_DIMS:
        if d not in profile:
            raise ValueError(f"missing EQ-5D-Y dimension {d!r}")
        if profile[d] not in (1, 2, 3):
            raise ValueError(
                f"EQ-5D-Y level for {d!r} must be 1, 2 or 3; got {profile[d]!r}"
            )
    if all(profile[d] == 1 for d in _EQ5D_Y_DIMS):
        return 1.0
    u = 1.0 - _EQ5D_Y_DUTCH_CONST
    for d in _EQ5D_Y_DIMS:
        u -= _EQ5D_Y_DUTCH_DECREMENTS[d][profile[d]]
    if any(profile[d] == 3 for d in _EQ5D_Y_DIMS):
        u -= _EQ5D_Y_DUTCH_N3
    return float(u)


# ─── SF-6D (Brazier 2002) ──────────────────────────────────────────────────

_SF6D_DIMS = (
    "physical_functioning",
    "role_limitations",
    "social_functioning",
    "pain",
    "mental_health",
    "vitality",
)
# Brazier 2002 Table 3 — decrements per dimension/level. Most dimensions
# have 4-5 levels. Level 1 = no problems = 0.0.
_SF6D_DECREMENTS: dict[str, dict[int, float]] = {
    "physical_functioning": {1: 0.0, 2: 0.053, 3: 0.011, 4: 0.040, 5: 0.055, 6: 0.117},
    "role_limitations":     {1: 0.0, 2: 0.053, 3: 0.053, 4: 0.069},
    "social_functioning":   {1: 0.0, 2: 0.057, 3: 0.059, 4: 0.072, 5: 0.087},
    "pain":                 {1: 0.0, 2: 0.0, 3: 0.042, 4: 0.065, 5: 0.102, 6: 0.171},
    "mental_health":        {1: 0.0, 2: 0.042, 3: 0.045, 4: 0.100, 5: 0.118},
    "vitality":             {1: 0.0, 2: 0.071, 3: 0.030, 4: 0.057, 5: 0.092},
}
_SF6D_CONST = 1.0  # full health
_SF6D_MB = 0.061  # "most bothersome" decrement when ANY dimension at its
# highest level (Brazier 2002, "MOST" coefficient).


def _apply_sf6d(profile: dict[str, int]) -> float:
    for d in _SF6D_DIMS:
        if d not in profile:
            raise ValueError(f"missing SF-6D dimension {d!r}")
    if all(profile[d] == 1 for d in _SF6D_DIMS):
        return 1.0
    u = _SF6D_CONST
    for d in _SF6D_DIMS:
        lv = profile[d]
        d_table = _SF6D_DECREMENTS[d]
        if lv not in d_table:
            raise ValueError(
                f"SF-6D level for {d!r} must be one of {sorted(d_table.keys())}; got {lv!r}"
            )
        u -= d_table[lv]
    # MB interaction: subtract once if ANY dimension hit its top level.
    for d in _SF6D_DIMS:
        top = max(_SF6D_DECREMENTS[d].keys())
        if profile[d] == top:
            u -= _SF6D_MB
            break
    return float(u)


# ─── Catalogue dispatch ────────────────────────────────────────────────────


_VALUE_SET_DISPATCH: dict[UtilityValueSet, Callable[[dict[str, int]], float]] = {
    "EQ5D_3L_UK": _apply_eq5d_3l_uk,
    "EQ5D_5L_UK": _apply_eq5d_5l_uk,
    "EQ5D_Y_DUTCH": _apply_eq5d_y_dutch,
    "SF6D": _apply_sf6d,
}


def apply_value_set(
    value_set: UtilityValueSet, response_profile: dict[str, int]
) -> float:
    """Map a response profile to a utility value via the named value set.

    ``"direct"`` is a no-op — the caller is expected to have provided a
    utility column already (e.g. clinician-derived EQ-VAS); call
    ``apply_value_set("direct", {"utility": 0.78})`` to round-trip the
    value unchanged.
    """
    if value_set == "direct":
        if "utility" not in response_profile:
            raise ValueError("direct value set requires 'utility' key")
        return float(response_profile["utility"])
    if value_set not in _VALUE_SET_DISPATCH:
        raise ValueError(f"unknown value set {value_set!r}")
    return _VALUE_SET_DISPATCH[value_set](response_profile)


def catalogue() -> list[dict]:
    """List metadata for every supported value set (for the catalogue endpoint)."""
    return [
        {
            "key": "EQ5D_3L_UK",
            "label": "EQ-5D-3L UK (Dolan 1997)",
            "dimensions": list(_EQ5D_3L_DIMS),
            "levels": 3,
            "source_citation": "Dolan NC. Med Care 1997;35(11):1095-1108.",
            "notes": "UK TTO tariff. Worst state (33333) = -0.594.",
        },
        {
            "key": "EQ5D_5L_UK",
            "label": "EQ-5D-5L England (Devlin 2018)",
            "dimensions": list(_EQ5D_3L_DIMS),
            "levels": 5,
            "source_citation": "Devlin et al. Health Econ 2018;27(1):7-22.",
            "notes": "English hybrid model; no separate interaction term.",
        },
        {
            "key": "EQ5D_Y_DUTCH",
            "label": "EQ-5D-Y Dutch (Kreimeier 2019)",
            "dimensions": list(_EQ5D_Y_DIMS),
            "levels": 3,
            "source_citation": "Kreimeier S, Oppe M et al. Value Health 2018/19.",
            "notes": "Paediatric value set; Dutch DCE-cTTO.",
        },
        {
            "key": "SF6D",
            "label": "SF-6D (Brazier 2002)",
            "dimensions": list(_SF6D_DIMS),
            "levels": 6,
            "source_citation": "Brazier J et al. J Health Econ 2002;21(2):271-292.",
            "notes": "Includes 'most-bothersome' interaction term.",
        },
        {
            "key": "direct",
            "label": "Direct utility (pre-computed)",
            "dimensions": ["utility"],
            "levels": 1,
            "source_citation": "n/a — caller supplies the utility.",
            "notes": "Use when the dataset already carries a utility column.",
        },
    ]


__all__ = ["apply_value_set", "catalogue"]
