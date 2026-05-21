/**
 * Phase 5b — LearnPage checklists tab.
 *
 * Mounts LearnPage on the Checklists tab, verifies that the list renders
 * the seeded checklist summaries and that the reporting-standard badge
 * appears next to the title.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api', () => {
  const checklists = [
    {
      slug: 'consort',
      title: 'CONSORT 2010 — Randomised controlled trials',
      reporting_standard: 'CONSORT',
      applies_to_study_types: ['parallel-group RCT'],
      version: '2010',
      short_blurb: 'Use CONSORT for every randomised controlled trial.',
      worked_example_domain: 'surgery',
    },
    {
      slug: 'prisma',
      title: 'PRISMA 2020 — Systematic reviews and meta-analyses',
      reporting_standard: 'PRISMA',
      applies_to_study_types: ['systematic review'],
      version: '2020',
      short_blurb: 'PRISMA 2020 supersedes PRISMA 2009.',
      worked_example_domain: 'orthopaedics',
    },
  ]
  return {
    learnApi: {
      listStatTests: vi.fn(async () => []),
      getStatTest: vi.fn(async () => null),
      listChecklists: vi.fn(async () => checklists),
      getChecklist: vi.fn(async (slug: string) => ({
        slug,
        title: checklists.find((c) => c.slug === slug)?.title ?? slug,
        reporting_standard:
          checklists.find((c) => c.slug === slug)?.reporting_standard ?? 'X',
        applies_to_study_types: ['parallel-group RCT'],
        version: '2010',
        official_url: 'https://www.equator-network.org/reporting-guidelines/consort/',
        worked_example_domain: 'surgery',
        related_concepts: [],
        body_md: '## CONSORT body\n\n- [ ] item 1\n- [ ] item 2',
      })),
      listEconomics: vi.fn(async () => []),
      getEconomics: vi.fn(async () => null),
      listSubmission: vi.fn(async () => []),
      getSubmission: vi.fn(async () => null),
      search: vi.fn(async () => []),
    },
  }
})

import LearnPage from '../LearnPage'

function wrap(initialEntry = '/projects/p-1/learn?cat=checklists') {
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

describe('LearnPage — checklists tab', () => {
  it('renders the checklist list with reporting-standard badges', async () => {
    wrap()
    expect(await screen.findByTestId('learn-entry-consort')).toBeDefined()
    expect(screen.getByTestId('learn-entry-prisma')).toBeDefined()
    // The badge next to the title should carry the reporting standard.
    expect(screen.getByTestId('learn-badge-consort').textContent).toContain(
      'CONSORT',
    )
    expect(screen.getByTestId('learn-badge-prisma').textContent).toContain(
      'PRISMA',
    )
  })

  it('shows the reporting standard badge in the detail pane on first render', async () => {
    wrap('/projects/p-1/learn?cat=checklists&slug=consort')
    expect(await screen.findByTestId('learn-detail-standard')).toBeDefined()
    expect(screen.getByTestId('learn-detail-standard').textContent).toContain(
      'CONSORT',
    )
  })
})
