/**
 * Client-side parity port of `services/review/rob_rules.py:derive_overall`.
 *
 * Keeps a *live preview* of the overall RoB judgement in the assessment form,
 * before the user hits save. The server is the source of truth — every POST/
 * PATCH re-derives this value server-side. This module mirrors the rule set
 * exactly:
 *   - RoB 2: high if any "high"; some_concerns if any "some_concerns";
 *     unclear if any "unclear"; otherwise low.
 *   - ROBINS-I: worst-domain ranking { low < moderate < no_information <
 *     serious < critical }, then mapped to the unified scale.
 *   - NOS: star total = count of "yes" answers across 3 domains; >=7 → low,
 *     >=5 → some_concerns, else high.
 *   - AMSTAR-2: critical-flaw counting (server holds the list of critical
 *     items — we accept a `criticalKeys` set so we don't need to duplicate
 *     it here).
 *
 * Verify parity with `apps/api/.../services/review/rob_rules.py` whenever the
 * server-side rules change.
 */

import type { RoBJudgement, RoBTool } from './api'

const ROBINSI_RANK: Record<string, number> = {
  low: 0,
  moderate: 1,
  no_information: 2,
  serious: 3,
  critical: 4,
}

const ROBINSI_MAP: Record<string, RoBJudgement> = {
  low: 'low',
  moderate: 'some_concerns',
  no_information: 'unclear',
  serious: 'high',
  critical: 'critical',
}

const AMSTAR2_UNIFIED: Record<string, RoBJudgement> = {
  high: 'low',
  moderate: 'some_concerns',
  low: 'high',
  critical_low: 'critical',
}

function rob2Overall(answers: Record<string, string>): RoBJudgement {
  let hasHigh = false
  let hasSome = false
  let hasUnclear = false
  for (const v of Object.values(answers)) {
    if (v === 'high') hasHigh = true
    else if (v === 'some_concerns') hasSome = true
    else if (v === 'unclear') hasUnclear = true
  }
  if (hasHigh) return 'high'
  if (hasSome) return 'some_concerns'
  if (hasUnclear) return 'unclear'
  return 'low'
}

function robinsiOverall(answers: Record<string, string>): RoBJudgement {
  const vals = Object.values(answers)
  if (vals.length === 0) return 'low'
  let worst = vals[0]
  for (const v of vals) {
    if ((ROBINSI_RANK[v] ?? -1) > (ROBINSI_RANK[worst] ?? -1)) worst = v
  }
  return ROBINSI_MAP[worst] ?? 'unclear'
}

function nosOverall(answers: Record<string, string>): RoBJudgement {
  let stars = 0
  for (const v of Object.values(answers)) {
    if (v === 'yes') stars += 1
  }
  if (stars >= 7) return 'low'
  if (stars >= 5) return 'some_concerns'
  return 'high'
}

function amstar2Overall(
  answers: Record<string, string>,
  criticalKeys: Set<string>,
): RoBJudgement {
  let crit = 0
  let noncrit = 0
  for (const [k, v] of Object.entries(answers)) {
    const isWeak = v !== 'yes'
    if (!isWeak) continue
    if (criticalKeys.has(k)) crit += 1
    else noncrit += 1
  }
  let raw: keyof typeof AMSTAR2_UNIFIED
  if (crit >= 2) raw = 'critical_low'
  else if (crit === 1) raw = 'low'
  else if (noncrit > 1) raw = 'moderate'
  else raw = 'high'
  return AMSTAR2_UNIFIED[raw]
}

export function deriveOverall(
  tool: RoBTool,
  domainAnswers: Record<string, string>,
  criticalKeys: Set<string> = new Set(),
): RoBJudgement {
  if (tool === 'rob2') return rob2Overall(domainAnswers)
  if (tool === 'robins_i') return robinsiOverall(domainAnswers)
  if (tool === 'nos') return nosOverall(domainAnswers)
  if (tool === 'amstar2') return amstar2Overall(domainAnswers, criticalKeys)
  return 'unclear'
}

/** Recommended tool based on an article's study_design field. */
export function recommendToolForDesign(
  design: string | null | undefined,
): RoBTool {
  if (!design) return 'rob2'
  const d = design.toLowerCase()
  if (
    d === 'rct' ||
    d.startsWith('randomi') ||
    d.includes('randomized_controlled')
  ) {
    return 'rob2'
  }
  if (d === 'systematic_review' || d === 'meta_analysis') return 'amstar2'
  if (
    d === 'cohort' ||
    d === 'case_control' ||
    d === 'non_randomised' ||
    d === 'observational' ||
    d === 'case_series' ||
    d === 'cross_sectional'
  ) {
    return 'robins_i'
  }
  return 'rob2'
}
