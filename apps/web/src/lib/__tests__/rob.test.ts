import { describe, expect, it } from 'vitest'

import { deriveOverall, recommendToolForDesign } from '../rob'

describe('deriveOverall — RoB 2 parity', () => {
  it('low when all low', () => {
    expect(
      deriveOverall('rob2', {
        randomisation: 'low',
        deviations: 'low',
        missing_outcome: 'low',
        measurement: 'low',
        reporting: 'low',
      }),
    ).toBe('low')
  })

  it('some_concerns when any some_concerns and no high', () => {
    expect(
      deriveOverall('rob2', {
        randomisation: 'low',
        deviations: 'some_concerns',
        missing_outcome: 'low',
        measurement: 'low',
        reporting: 'low',
      }),
    ).toBe('some_concerns')
  })

  it('high when any high', () => {
    expect(
      deriveOverall('rob2', {
        randomisation: 'low',
        deviations: 'some_concerns',
        missing_outcome: 'high',
        measurement: 'low',
        reporting: 'low',
      }),
    ).toBe('high')
  })

  it('unclear when only unclear/low present', () => {
    expect(
      deriveOverall('rob2', {
        randomisation: 'unclear',
        deviations: 'low',
      }),
    ).toBe('unclear')
  })
})

describe('deriveOverall — ROBINS-I parity', () => {
  it('maps worst domain by rank', () => {
    expect(
      deriveOverall('robins_i', {
        confounding: 'low',
        selection: 'serious',
        classification: 'moderate',
      }),
    ).toBe('high')
  })

  it('critical → critical', () => {
    expect(
      deriveOverall('robins_i', { confounding: 'critical', selection: 'low' }),
    ).toBe('critical')
  })

  it('no_information → unclear when worst', () => {
    expect(
      deriveOverall('robins_i', {
        confounding: 'low',
        selection: 'no_information',
      }),
    ).toBe('unclear')
  })
})

describe('deriveOverall — NOS parity', () => {
  it('>=7 stars → low', () => {
    const ans: Record<string, string> = {}
    for (let i = 0; i < 7; i++) ans[`d${i}`] = 'yes'
    expect(deriveOverall('nos', ans)).toBe('low')
  })

  it('5-6 stars → some_concerns', () => {
    const ans: Record<string, string> = {}
    for (let i = 0; i < 5; i++) ans[`d${i}`] = 'yes'
    expect(deriveOverall('nos', ans)).toBe('some_concerns')
  })

  it('<5 stars → high', () => {
    expect(deriveOverall('nos', { d1: 'yes', d2: 'no' })).toBe('high')
  })
})

describe('deriveOverall — AMSTAR-2 parity', () => {
  const critical = new Set(['a2_2', 'a2_4', 'a2_7', 'a2_9', 'a2_11', 'a2_13', 'a2_15'])

  it('all yes → low (unified)', () => {
    const ans: Record<string, string> = {}
    for (const k of critical) ans[k] = 'yes'
    expect(deriveOverall('amstar2', ans, critical)).toBe('low')
  })

  it('one critical no → high (unified low)', () => {
    const ans: Record<string, string> = {}
    for (const k of critical) ans[k] = 'yes'
    ans['a2_2'] = 'no'
    expect(deriveOverall('amstar2', ans, critical)).toBe('high')
  })

  it('two critical no → critical', () => {
    const ans: Record<string, string> = {}
    for (const k of critical) ans[k] = 'yes'
    ans['a2_2'] = 'no'
    ans['a2_4'] = 'no'
    expect(deriveOverall('amstar2', ans, critical)).toBe('critical')
  })
})

describe('recommendToolForDesign', () => {
  it('RCT → rob2', () => {
    expect(recommendToolForDesign('RCT')).toBe('rob2')
  })
  it('cohort → robins_i', () => {
    expect(recommendToolForDesign('cohort')).toBe('robins_i')
  })
  it('null defaults to rob2', () => {
    expect(recommendToolForDesign(null)).toBe('rob2')
  })
})
