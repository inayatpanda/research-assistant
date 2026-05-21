/**
 * Phase 5c — LearnPage walkthroughs tab + cross-category search.
 *
 * Mounts LearnPage with mocked walkthrough fixtures and verifies:
 *   1. The walkthroughs tab lists every walkthrough summary.
 *   2. The detail pane renders with the TOC sidebar, reading-time chip,
 *      and Markdown body once an entry is selected.
 *   3. Typing into the search input triggers the cross-category search
 *      endpoint and renders grouped hits.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api', () => {
  const walkthroughs = [
    {
      slug: 'systematic-review-from-scratch',
      title: 'Running a systematic review from scratch',
      study_type: 'systematic_review',
      estimated_reading_minutes: 22,
      sections: ['PICO and the protocol', 'Search strategy', 'Screening'],
      short_blurb:
        'End-to-end review of ACL reconstruction outcomes — PICO, search, RoB, GRADE, write-up.',
      worked_example_domain: 'orthopaedics',
    },
    {
      slug: 'rct-write-up',
      title: 'Writing up a randomised controlled trial',
      study_type: 'rct',
      estimated_reading_minutes: 20,
      sections: ['CONSORT', 'ITT', 'ANCOVA'],
      short_blurb:
        'Antihypertensive trial — locked dataset, CONSORT flow, ANCOVA, ITT, sensitivity.',
      worked_example_domain: 'medicine',
    },
  ]
  const detail = {
    slug: 'systematic-review-from-scratch',
    title: 'Running a systematic review from scratch',
    study_type: 'systematic_review',
    estimated_reading_minutes: 22,
    sections: ['PICO and the protocol', 'Search strategy'],
    worked_example_domain: 'orthopaedics',
    related_concepts: ['prisma', 'rob2', 'grade'],
    body_md:
      '# Walkthrough\n\n## PICO and the protocol\n\nDefine your PICO question carefully.\n\n## Search strategy\n\nWrite MeSH queries with synonyms.\n',
  }
  const crossHits = [
    {
      category: 'walkthroughs',
      slug: 'systematic-review-from-scratch',
      title: 'Running a systematic review from scratch',
      snippet: '… PRISMA flow chart in the Figures tab populates itself …',
    },
    {
      category: 'checklists',
      slug: 'prisma',
      title: 'PRISMA 2020',
      snippet: '… 27-item PRISMA checklist drives the methods section …',
    },
  ]
  return {
    learnApi: {
      listStatTests: vi.fn(async () => []),
      getStatTest: vi.fn(async () => null),
      listChecklists: vi.fn(async () => []),
      getChecklist: vi.fn(async () => null),
      listEconomics: vi.fn(async () => []),
      getEconomics: vi.fn(async () => null),
      listSubmission: vi.fn(async () => []),
      getSubmission: vi.fn(async () => null),
      listWalkthroughs: vi.fn(async () => walkthroughs),
      getWalkthrough: vi.fn(async () => detail),
      search: vi.fn(async () => crossHits),
    },
  }
})

import LearnPage from '../LearnPage'

function wrap(initialPath = '/projects/p-1/learn?cat=walkthroughs') {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/projects/:projectId/learn" element={<LearnPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(cleanup)

describe('LearnPage — walkthroughs', () => {
  it('lists walkthrough summaries under the walkthroughs tab', async () => {
    wrap()
    expect(
      await screen.findByTestId('learn-entry-systematic-review-from-scratch'),
    ).toBeDefined()
    expect(screen.getByTestId('learn-entry-rct-write-up')).toBeDefined()
  })

  it('renders the walkthrough detail with reading-time chip + TOC sidebar', async () => {
    wrap()
    await screen.findByTestId('learn-entry-systematic-review-from-scratch')
    // First entry is auto-selected so detail should render.
    expect(await screen.findByTestId('walkthrough-detail')).toBeDefined()
    expect(screen.getByTestId('walkthrough-reading-time')).toBeDefined()
    expect(screen.getByTestId('walkthrough-toc')).toBeDefined()
    expect(screen.getByTestId('walkthrough-toc').textContent).toContain(
      'PICO and the protocol',
    )
    expect(screen.getByTestId('walkthrough-toc').textContent).toContain(
      'Search strategy',
    )
  })

  it('shows cross-category hits when the search input has >=2 chars', async () => {
    wrap('/projects/p-1/learn?cat=stat-tests')
    const input = (await screen.findByTestId(
      'learn-search-input',
    )) as HTMLInputElement
    await act(async () => {
      fireEvent.change(input, { target: { value: 'prisma' } })
    })
    // Cross-category hits panel should appear with at least one bucket.
    expect(await screen.findByTestId('learn-cross-hits')).toBeDefined()
    expect(
      screen.getByTestId('learn-cross-hit-systematic-review-from-scratch'),
    ).toBeDefined()
    expect(screen.getByTestId('learn-cross-hit-prisma')).toBeDefined()
  })
})
