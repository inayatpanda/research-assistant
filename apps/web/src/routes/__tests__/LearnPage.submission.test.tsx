/**
 * Phase 5b — LearnPage submission tab.
 *
 * Verifies the list groups topics by topic_family in the spec'd order
 * (planning before writing before submitting before post-decision).
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api', () => {
  const submission = [
    {
      slug: 'cover-letter',
      title: 'Cover letter',
      topic: 'cover-letter',
      topic_family: 'writing',
      short_blurb: 'A cover letter is a short, one-page note to the editor.',
      worked_example_domain: 'medicine',
    },
    {
      slug: 'picking-a-journal',
      title: 'Picking a journal',
      topic: 'picking-a-journal',
      topic_family: 'planning',
      short_blurb: 'Choose where to submit before you write the introduction.',
      worked_example_domain: 'orthopaedics',
    },
    {
      slug: 'response-to-reviewers',
      title: 'Response to reviewers',
      topic: 'response-to-reviewers',
      topic_family: 'post-decision',
      short_blurb: 'A point-by-point document responding to every reviewer comment.',
      worked_example_domain: 'orthopaedics',
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
      listSubmission: vi.fn(async () => submission),
      getSubmission: vi.fn(async (slug: string) => ({
        slug,
        title: submission.find((s) => s.slug === slug)?.title ?? slug,
        topic: submission.find((s) => s.slug === slug)?.topic ?? slug,
        topic_family:
          submission.find((s) => s.slug === slug)?.topic_family ?? 'writing',
        worked_example_domain: 'medicine',
        related_concepts: [],
        body_md: '## Cover letter\n\nLorem ipsum',
      })),
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
      <MemoryRouter initialEntries={['/projects/p-1/learn?cat=submission']}>
        <Routes>
          <Route path="/projects/:projectId/learn" element={<LearnPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(cleanup)

describe('LearnPage — submission tab', () => {
  it('groups submission topics by family in planning -> writing -> post-decision order', async () => {
    wrap()
    expect(await screen.findByTestId('learn-entry-picking-a-journal')).toBeDefined()
    expect(screen.getByTestId('learn-entry-cover-letter')).toBeDefined()
    expect(screen.getByTestId('learn-entry-response-to-reviewers')).toBeDefined()

    // Confirm the spec'd family ordering by reading the list DOM order.
    const list = screen.getByTestId('learn-entry-list')
    const text = list.textContent ?? ''
    const planningIdx = text.indexOf('Picking a journal')
    const writingIdx = text.indexOf('Cover letter')
    const postIdx = text.indexOf('Response to reviewers')
    expect(planningIdx).toBeGreaterThanOrEqual(0)
    expect(writingIdx).toBeGreaterThan(planningIdx)
    expect(postIdx).toBeGreaterThan(writingIdx)
  })
})
