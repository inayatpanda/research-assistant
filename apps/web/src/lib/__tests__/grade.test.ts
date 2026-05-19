import { describe, expect, it } from 'vitest'

import { deriveCertainty } from '../grade'

const NO_DOWN = {
  risk_of_bias: 'not_serious',
  inconsistency: 'not_serious',
  indirectness: 'not_serious',
  imprecision: 'not_serious',
  publication_bias: 'not_serious',
} as const

const NO_UP = {
  large_effect: 'none',
  dose_response: 'none',
  confounders_against: 'none',
} as const

describe('deriveCertainty — JS mirror of services/review/grade.py', () => {
  it('returns high for an RCT with no downgrades and no upgrades', () => {
    expect(deriveCertainty('high', NO_DOWN, NO_UP)).toBe('high')
  })

  it('returns moderate when exactly one downgrade is serious', () => {
    expect(
      deriveCertainty(
        'high',
        { ...NO_DOWN, risk_of_bias: 'serious' },
        NO_UP,
      ),
    ).toBe('moderate')
  })

  it('returns low when two downgrades are serious', () => {
    expect(
      deriveCertainty(
        'high',
        { ...NO_DOWN, risk_of_bias: 'serious', inconsistency: 'serious' },
        NO_UP,
      ),
    ).toBe('low')
  })

  it('one very_serious downgrade drops two bands', () => {
    expect(
      deriveCertainty(
        'high',
        { ...NO_DOWN, imprecision: 'very_serious' },
        NO_UP,
      ),
    ).toBe('low')
  })

  it('observational baseline + large effect (large) lifts to high', () => {
    expect(
      deriveCertainty('low', NO_DOWN, { ...NO_UP, large_effect: 'large' }),
    ).toBe('high')
  })

  it('upgrades are ignored when a downgrade is present', () => {
    expect(
      deriveCertainty(
        'high',
        { ...NO_DOWN, risk_of_bias: 'serious' },
        { ...NO_UP, large_effect: 'large' },
      ),
    ).toBe('moderate')
  })

  it('floors at very_low even with extreme downgrades', () => {
    const everywhere = {
      risk_of_bias: 'very_serious',
      inconsistency: 'very_serious',
      indirectness: 'very_serious',
      imprecision: 'very_serious',
      publication_bias: 'very_serious',
    } as const
    expect(deriveCertainty('high', everywhere, NO_UP)).toBe('very_low')
  })
})
