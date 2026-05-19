/**
 * Phase 14 (MP14) — vitest for GRADEAssessmentForm.
 *
 * Exercises the live-derivation badge. We don't drive Radix Select (brittle
 * in jsdom); instead we render with an `existing` row and assert that the
 * badge reflects the seeded state, then re-render with a different seeded
 * row and assert the badge updates.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

beforeAll(() => {
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = vi.fn()
  }
  if (!('hasPointerCapture' in Element.prototype)) {
    Element.prototype.hasPointerCapture = vi.fn(() => false)
    Element.prototype.releasePointerCapture = vi.fn()
  }
})

import type { GradeAssessmentRead } from '@/lib/api'
import { GRADEAssessmentForm } from '../GRADEAssessmentForm'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  )
}

function makeExisting(overrides: Partial<GradeAssessmentRead> = {}): GradeAssessmentRead {
  return {
    id: 'g-1',
    project_id: 'p-1',
    review_id: 'r-1',
    meta_id: null,
    outcome_label: 'Mortality',
    starting_certainty: 'high',
    domain_risk_of_bias: 'not_serious',
    domain_inconsistency: 'not_serious',
    domain_indirectness: 'not_serious',
    domain_imprecision: 'not_serious',
    domain_publication_bias: 'not_serious',
    upgrade_large_effect: 'none',
    upgrade_dose_response: 'none',
    upgrade_confounders_against: 'none',
    certainty: 'high',
    notes: null,
    created_at: '2026-05-18T00:00:00Z',
    updated_at: '2026-05-18T00:00:00Z',
    ...overrides,
  }
}

afterEach(() => cleanup())

describe('GRADEAssessmentForm', () => {
  it('renders the high certainty badge for a no-downgrade RCT seed', () => {
    wrap(
      <GRADEAssessmentForm
        projectId="p-1"
        existing={makeExisting()}
      />,
    )
    const badge = screen.getByTestId('grade-certainty-badge')
    expect(badge.getAttribute('data-certainty')).toBe('high')
    expect(badge.textContent).toContain('High')
  })

  it('renders the moderate badge when one downgrade domain is serious', () => {
    wrap(
      <GRADEAssessmentForm
        projectId="p-1"
        existing={makeExisting({ domain_risk_of_bias: 'serious' })}
      />,
    )
    const badge = screen.getByTestId('grade-certainty-badge')
    expect(badge.getAttribute('data-certainty')).toBe('moderate')
  })

  it('serialises the outcome label into the input for the user to edit', () => {
    wrap(
      <GRADEAssessmentForm
        projectId="p-1"
        existing={makeExisting({ outcome_label: 'Stroke at 12 months' })}
      />,
    )
    const input = screen.getByTestId('grade-outcome') as HTMLInputElement
    expect(input.value).toBe('Stroke at 12 months')
  })
})
