/**
 * Phase 14 (MP14) — Mirror of the backend GRADE certainty derivation.
 *
 * Kept in sync with services/review/grade.py. Pure function — no React, no
 * network. Used by the GRADE assessment form to surface the derived
 * certainty live as the user toggles each domain.
 */
import type {
  GradeCertainty,
  GradeDowngradeLevel,
  GradeStartingCertainty,
  GradeUpgradeLevel,
  GradeSmallUpgrade,
} from './api'

const STARTING_BAND: Record<GradeStartingCertainty, number> = {
  high: 4,
  low: 2,
}

const DOWNGRADE_DELTA: Record<GradeDowngradeLevel, number> = {
  not_serious: 0,
  serious: -1,
  very_serious: -2,
}

const LARGE_EFFECT_DELTA: Record<GradeUpgradeLevel, number> = {
  none: 0,
  present: 1,
  large: 2,
}

const SMALL_UPGRADE_DELTA: Record<GradeUpgradeLevel, number> = {
  none: 0,
  present: 1,
  large: 1,
}

const BAND_TO_CERTAINTY: Record<number, GradeCertainty> = {
  4: 'high',
  3: 'moderate',
  2: 'low',
  1: 'very_low',
}

export type DowngradeDomains = {
  risk_of_bias: GradeDowngradeLevel
  inconsistency: GradeDowngradeLevel
  indirectness: GradeDowngradeLevel
  imprecision: GradeDowngradeLevel
  publication_bias: GradeDowngradeLevel
}

export type UpgradeDomains = {
  large_effect: GradeUpgradeLevel
  dose_response: GradeSmallUpgrade
  confounders_against: GradeSmallUpgrade
}

export function deriveCertainty(
  starting: GradeStartingCertainty,
  downgrades: DowngradeDomains,
  upgrades: UpgradeDomains,
): GradeCertainty {
  const base = STARTING_BAND[starting]

  let downNet = 0
  for (const v of Object.values(downgrades)) {
    downNet += DOWNGRADE_DELTA[v]
  }

  let upGross = 0
  upGross += LARGE_EFFECT_DELTA[upgrades.large_effect]
  upGross += SMALL_UPGRADE_DELTA[upgrades.dose_response as GradeUpgradeLevel]
  upGross +=
    SMALL_UPGRADE_DELTA[upgrades.confounders_against as GradeUpgradeLevel]

  // Per GRADE: upgrades only count when no downgrade is present.
  const net = downNet < 0 ? downNet : upGross

  const band = Math.max(1, Math.min(4, base + net))
  return BAND_TO_CERTAINTY[band]
}

export const CERTAINTY_LABEL: Record<GradeCertainty, string> = {
  high: 'High',
  moderate: 'Moderate',
  low: 'Low',
  very_low: 'Very low',
}

export const CERTAINTY_SYMBOL: Record<GradeCertainty, string> = {
  high: '⊕⊕⊕⊕',
  moderate: '⊕⊕⊕⊖',
  low: '⊕⊕⊖⊖',
  very_low: '⊕⊖⊖⊖',
}
