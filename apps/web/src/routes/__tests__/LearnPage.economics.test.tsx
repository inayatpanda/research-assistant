/**
 * Phase 5b — LearnPage economics tab.
 *
 * Verifies the list renders concept-family groupings and that the
 * detail pane displays the formula block.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api', () => {
  const economics = [
    {
      slug: 'incremental-cost-effectiveness-ratio',
      title: 'Incremental cost-effectiveness ratio (ICER)',
      concept_family: 'cost-effectiveness',
      formula:
        'ICER = (Cost_new - Cost_comparator) / (Effect_new - Effect_comparator)',
      units: '£/QALY',
      short_blurb:
        'The incremental cost-effectiveness ratio summarises one strategy versus another.',
      worked_example_domain: 'orthopaedics',
    },
    {
      slug: 'quality-adjusted-life-year',
      title: 'Quality-adjusted life-year (QALY)',
      concept_family: 'outcomes-measurement',
      formula: 'QALY = Sum(utility × duration)',
      units: 'QALYs',
      short_blurb: 'One QALY equals one year in perfect health.',
      worked_example_domain: 'medicine',
    },
  ]
  return {
    learnApi: {
      listStatTests: vi.fn(async () => []),
      getStatTest: vi.fn(async () => null),
      listChecklists: vi.fn(async () => []),
      getChecklist: vi.fn(async () => null),
      listEconomics: vi.fn(async () => economics),
      getEconomics: vi.fn(async (slug: string) => ({
        slug,
        title: economics.find((e) => e.slug === slug)?.title ?? slug,
        concept_family:
          economics.find((e) => e.slug === slug)?.concept_family ?? 'X',
        formula: economics.find((e) => e.slug === slug)?.formula ?? '',
        units: economics.find((e) => e.slug === slug)?.units ?? '',
        worked_example_domain: 'orthopaedics',
        related_concepts: [],
        body_md: '## ICER\n\nLorem ipsum',
      })),
      listSubmission: vi.fn(async () => []),
      getSubmission: vi.fn(async () => null),
      search: vi.fn(async () => []),
    },
  }
})

import LearnPage from '../LearnPage'

function wrap(initialEntry = '/projects/p-1/learn?cat=economics') {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/projects/:projectId/learn" element={<LearnPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(cleanup)

describe('LearnPage — economics tab', () => {
  it('renders economics entries grouped by concept family with formula block', async () => {
    wrap('/projects/p-1/learn?cat=economics&slug=incremental-cost-effectiveness-ratio')
    expect(
      await screen.findByTestId('learn-entry-incremental-cost-effectiveness-ratio'),
    ).toBeDefined()
    expect(screen.getByTestId('learn-entry-quality-adjusted-life-year')).toBeDefined()
    // Formula text should appear in the detail pane.
    const detailPane = screen.getByTestId('learn-detail-pane')
    expect(detailPane.textContent).toContain('ICER = (Cost_new')
  })
})
