/**
 * Phase 5a — LearnPage smoke test.
 *
 * Mounts LearnPage with mocked learnApi data and verifies:
 *   1. The list renders the seeded stat-test summaries.
 *   2. Typing into the search box filters the visible entries.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api', () => {
  const summaries = [
    {
      slug: 'independent-t-test',
      title: 'Independent samples t-test',
      family: 'comparison_of_means',
      short_blurb: 'Compare means of one continuous variable across two groups.',
      worked_example_domain: 'orthopaedics',
    },
    {
      slug: 'mann-whitney-u',
      title: 'Mann-Whitney U test',
      family: 'non_parametric_comparison',
      short_blurb: 'Compare distributions of two independent groups non-parametrically.',
      worked_example_domain: 'medicine',
    },
    {
      slug: 'kaplan-meier-log-rank',
      title: 'Kaplan-Meier survival + log-rank test',
      family: 'survival',
      short_blurb: 'Estimate and compare survival functions.',
      worked_example_domain: 'orthopaedics',
    },
  ]
  const details: Record<string, unknown> = {
    'independent-t-test': {
      slug: 'independent-t-test',
      title: 'Independent samples t-test',
      family: 'comparison_of_means',
      when_to_use: 'Compare the means of one continuous variable across two groups.',
      assumptions: ['Continuous outcome', 'Normality in each group'],
      alternatives: ['mann-whitney-u'],
      worked_example_domain: 'orthopaedics',
      worked_example_dataset: 'knee_flexion_two_implants',
      related_concepts: ['confidence-intervals'],
      body_md:
        '# Independent samples t-test\n\n## When to use\n\nUse it when comparing two groups.\n',
    },
  }
  return {
    learnApi: {
      listStatTests: vi.fn(async () => summaries),
      getStatTest: vi.fn(async (slug: string) => details[slug]),
      listChecklists: vi.fn(async () => []),
      getChecklist: vi.fn(async () => null),
      listEconomics: vi.fn(async () => []),
      getEconomics: vi.fn(async () => null),
      listSubmission: vi.fn(async () => []),
      getSubmission: vi.fn(async () => null),
      search: vi.fn(async () => []),
    },
  }
})

import LearnPage from '../LearnPage'

function wrap() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/projects/p-1/learn']}>
        <Routes>
          <Route path="/projects/:projectId/learn" element={<LearnPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(cleanup)

describe('LearnPage', () => {
  it('renders the page shell and lists the seeded stat-test summaries', async () => {
    wrap()
    expect(screen.getByTestId('learn-page-shell')).toBeDefined()
    expect(screen.getByTestId('learn-category-tabs')).toBeDefined()
    expect(await screen.findByTestId('learn-entry-independent-t-test')).toBeDefined()
    expect(screen.getByTestId('learn-entry-mann-whitney-u')).toBeDefined()
    expect(screen.getByTestId('learn-entry-kaplan-meier-log-rank')).toBeDefined()
  })

  it('filters the entry list when the user types in the search box', async () => {
    wrap()
    // Wait for the initial list to populate.
    await screen.findByTestId('learn-entry-independent-t-test')
    const input = screen.getByTestId('learn-search-input') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'mann' } })
    expect(screen.getByTestId('learn-entry-mann-whitney-u')).toBeDefined()
    expect(screen.queryByTestId('learn-entry-independent-t-test')).toBeNull()
    expect(screen.queryByTestId('learn-entry-kaplan-meier-log-rank')).toBeNull()
  })
})
