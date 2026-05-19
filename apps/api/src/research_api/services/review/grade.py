"""Phase 14 (MP14) — GRADE certainty-of-evidence derivation.

Pure function — no DB, no FS, no network. Given a starting certainty plus
five downgrade domains and three upgrade domains, returns the final
certainty band in {"high", "moderate", "low", "very_low"}.

Algorithm (per GRADE handbook):

  - Map the starting certainty to a numeric band:
      high → 4, low → 2.
  - Each downgrade contributes 0 / -1 / -2 for not_serious / serious /
    very_serious. The five downgrade domains sum together.
  - Upgrades only ever apply when there's no serious downgrade
    (per GRADE's own rule). We follow the conservative interpretation:
    upgrades may be present in the input but only count if the total
    downgrade sum is zero — otherwise they're clamped to zero.
  - When upgrades do count: large_effect can be 0 / +1 / +2, the other two
    cap at +1.
  - Final numeric band is clamped to [1, 4] and mapped:
      4 → "high", 3 → "moderate", 2 → "low", 1 → "very_low".
"""
from __future__ import annotations

from typing import Literal

StartingCertainty = Literal["high", "low"]
DowngradeLevel = Literal["not_serious", "serious", "very_serious"]
UpgradeLevel = Literal["none", "present", "large"]
Certainty = Literal["high", "moderate", "low", "very_low"]


_STARTING_BAND: dict[str, int] = {
    "high": 4,
    "low": 2,
}

_DOWNGRADE_DELTA: dict[str, int] = {
    "not_serious": 0,
    "serious": -1,
    "very_serious": -2,
}

_LARGE_EFFECT_DELTA: dict[str, int] = {
    "none": 0,
    "present": 1,
    "large": 2,
}

# Other upgrades cap at +1 even if "large" is somehow supplied.
_SMALL_UPGRADE_DELTA: dict[str, int] = {
    "none": 0,
    "present": 1,
    "large": 1,
}

_BAND_TO_CERTAINTY: dict[int, Certainty] = {
    4: "high",
    3: "moderate",
    2: "low",
    1: "very_low",
}


def _validate_downgrades(downgrades: dict[str, str]) -> int:
    """Return the (negative) net downgrade total."""
    total = 0
    for k, v in downgrades.items():
        delta = _DOWNGRADE_DELTA.get(v)
        if delta is None:
            raise ValueError(f"invalid downgrade level {v!r} for domain {k!r}")
        total += delta
    return total


def _validate_upgrades(upgrades: dict[str, str]) -> int:
    """Return the (positive) gross upgrade total."""
    total = 0
    for k, v in upgrades.items():
        if k == "large_effect":
            delta = _LARGE_EFFECT_DELTA.get(v)
        else:
            delta = _SMALL_UPGRADE_DELTA.get(v)
        if delta is None:
            raise ValueError(f"invalid upgrade level {v!r} for domain {k!r}")
        total += delta
    return total


def compute_certainty(
    starting: StartingCertainty,
    downgrades: dict[str, str],
    upgrades: dict[str, str],
) -> Certainty:
    """Derive the GRADE certainty band.

    Args:
        starting: ``"high"`` for RCTs, ``"low"`` for observational studies.
        downgrades: dict of the five domain keys → not_serious / serious /
            very_serious. Missing keys are treated as ``not_serious``.
        upgrades: dict of three keys (``large_effect``, ``dose_response``,
            ``confounders_against``) → none / present / large. Missing keys
            are treated as ``none``.

    Returns:
        One of ``"high"``, ``"moderate"``, ``"low"``, ``"very_low"``.
    """
    base = _STARTING_BAND.get(starting)
    if base is None:
        raise ValueError(f"invalid starting certainty {starting!r}")

    down_net = _validate_downgrades(downgrades)
    up_gross = _validate_upgrades(upgrades)

    # Per GRADE: upgrades only count when no domain is serious/very_serious.
    if down_net < 0:
        net = down_net
    else:
        net = up_gross

    band = max(1, min(4, base + net))
    return _BAND_TO_CERTAINTY[band]
