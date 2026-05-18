import { describe, expect, it } from 'vitest'

import type { DatasetVariable, VariableType } from '@/lib/api'
import { typeWarningFor } from '../WizardVariableStep'

function makeVar(name: string, type: VariableType, userType: VariableType | null = null): DatasetVariable {
  return {
    id: `v-${name}`,
    dataset_id: 'ds-1',
    name,
    position: 0,
    inferred_type: type,
    user_type: userType,
    n_missing: 0,
    sample_values: [],
  }
}

describe('typeWarningFor', () => {
  it('returns null for a numeric outcome in a t-test', () => {
    const v = makeVar('age', 'numeric')
    expect(typeWarningFor(v, 'group_comparison', 'outcome')).toBeNull()
  })

  it('warns for a nominal outcome in a group_comparison (suggests chi-square / Mann-Whitney)', () => {
    const v = makeVar('sex', 'nominal')
    const w = typeWarningFor(v, 'group_comparison', 'outcome')
    expect(w).not.toBeNull()
    expect(w).toMatch(/chi-square|Mann-Whitney/i)
  })

  it('respects the user_type override over inferred_type', () => {
    const v = makeVar('age', 'nominal', 'numeric')
    expect(typeWarningFor(v, 'group_comparison', 'outcome')).toBeNull()
  })

  it('warns when event indicator is not 0/1', () => {
    const v = makeVar('status', 'nominal')
    expect(typeWarningFor(v, 'time_to_event', 'event')).not.toBeNull()
  })

  it('returns null when variable is undefined', () => {
    expect(typeWarningFor(undefined, 'group_comparison', 'outcome')).toBeNull()
  })

  it('returns null for roles without an expected-type rule', () => {
    const v = makeVar('rater', 'nominal')
    expect(typeWarningFor(v, 'agreement', 'rater_a')).toBeNull()
  })
})
