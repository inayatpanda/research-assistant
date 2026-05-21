/**
 * Phase M1.5 — MobileLearnEntryPage smoke tests.
 *
 *   1. Renders the markdown body for a stat-test entry.
 *   2. Tapping a related-concept chip navigates to that concept's
 *      entry route.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

const hoisted = vi.hoisted(() => ({
  getStatTest: vi.fn(async () => ({
    slug: 'wilcoxon',
    title: 'Wilcoxon signed-rank',
    family: 'non-parametric',
    when_to_use: 'Paired non-normal data.',
    assumptions: ['Paired'],
    alternatives: ['paired-t'],
    worked_example_domain: 'orthopaedics',
    worked_example_dataset: 'foo.csv',
    related_concepts: ['paired-t', 'sign-test'],
    body_md: '# Wilcoxon\n\nThis test compares paired samples.',
  })),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  return {
    ...actual,
    learnApi: {
      getStatTest: hoisted.getStatTest,
      getChecklist: vi.fn(),
      getEconomics: vi.fn(),
      getSubmission: vi.fn(),
      getWalkthrough: vi.fn(),
    },
  }
})

vi.mock('@/mobile/lib/offlineLearn', () => ({
  cacheable: async (_key: string, fetcher: () => Promise<unknown>) => ({
    data: await fetcher(),
    offline: false,
  }),
  entryKey: (c: string, s: string) => `${c}:${s}`,
  listKey: (c: string) => `__list:${c}`,
}))

import MobileLearnEntryPage from '@/mobile/pages/MobileLearnEntryPage'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            path="/m/learn/:category/:slug"
            element={<MobileLearnEntryPage />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('MobileLearnEntryPage', () => {
  it('renders the markdown body of the entry', async () => {
    renderAt('/m/learn/stat-tests/wilcoxon')
    await waitFor(() => {
      expect(screen.getByText(/This test compares paired samples\./)).toBeTruthy()
    })
  })

  it('navigates to a related concept when its chip is tapped', async () => {
    renderAt('/m/learn/stat-tests/wilcoxon')
    const related = await screen.findByTestId('mlearn-related-paired-t')
    fireEvent.click(related)
    // The new query goes back through the same mock; we just verify the
    // call was made with the new slug.
    await waitFor(() => {
      expect(hoisted.getStatTest).toHaveBeenLastCalledWith('paired-t')
    })
  })
})
