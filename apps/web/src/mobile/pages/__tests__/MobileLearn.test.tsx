/**
 * Phase M1.5 — MobileLearn smoke tests.
 *
 *   1. Category chip switches the visible list.
 *   2. Search debounces, then hits the cross-category endpoint.
 *   3. Tapping an entry navigates to the entry detail route.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

const hoisted = vi.hoisted(() => ({
  listStatTests: vi.fn(async () => [
    {
      slug: 'wilcoxon',
      title: 'Wilcoxon signed-rank',
      family: 'non-parametric',
      short_blurb: 'Compares paired samples without normality.',
      worked_example_domain: 'orthopaedics',
    },
  ]),
  listChecklists: vi.fn(async () => [
    {
      slug: 'consort-2010',
      title: 'CONSORT 2010',
      reporting_standard: 'CONSORT',
      applies_to_study_types: ['rct'],
      version: '2010',
      short_blurb: 'Reporting checklist for RCTs',
      worked_example_domain: 'orthopaedics',
    },
  ]),
  listEconomics: vi.fn(async () => []),
  listSubmission: vi.fn(async () => []),
  listWalkthroughs: vi.fn(async () => []),
  search: vi.fn(async () => [
    {
      category: 'stat-tests',
      slug: 'wilcoxon',
      title: 'Wilcoxon signed-rank',
      snippet: 'Paired-sample non-parametric test.',
    },
  ]),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  return {
    ...actual,
    learnApi: {
      listStatTests: hoisted.listStatTests,
      listChecklists: hoisted.listChecklists,
      listEconomics: hoisted.listEconomics,
      listSubmission: hoisted.listSubmission,
      listWalkthroughs: hoisted.listWalkthroughs,
      search: hoisted.search,
    },
  }
})

// Skip the IDB layer — the queryFn passes through `cacheable()` which
// would otherwise complain about missing IndexedDB in jsdom.
vi.mock('@/mobile/lib/offlineLearn', async () => ({
  cacheable: async (_key: string, fetcher: () => Promise<unknown>) => ({
    data: await fetcher(),
    offline: false,
  }),
  entryKey: (c: string, s: string) => `${c}:${s}`,
  listKey: (c: string) => `__list:${c}`,
}))

import MobileLearn from '@/mobile/pages/MobileLearn'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/m/learn" element={<MobileLearn />} />
          <Route
            path="/m/learn/:category/:slug"
            element={<div data-testid="entry-route">entry</div>}
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

describe('MobileLearn', () => {
  it('switches list when a category chip is clicked', async () => {
    renderAt('/m/learn')
    await waitFor(() => {
      expect(screen.getByTestId('mlearn-entry-wilcoxon')).toBeTruthy()
    })
    fireEvent.click(screen.getByTestId('mlearn-chip-checklists'))
    await waitFor(() => {
      expect(screen.getByTestId('mlearn-entry-consort-2010')).toBeTruthy()
    })
  })

  it('debounces search input and queries the cross-category endpoint', async () => {
    renderAt('/m/learn')
    await waitFor(() => expect(screen.getByTestId('mlearn-entry-wilcoxon')).toBeTruthy())
    const input = screen.getByTestId('mobile-learn-search') as HTMLInputElement
    // Type quickly — every keystroke under 250ms should NOT trigger
    // /api/learn/search.
    fireEvent.change(input, { target: { value: 'w' } })
    fireEvent.change(input, { target: { value: 'wi' } })
    fireEvent.change(input, { target: { value: 'wil' } })
    // Without waiting for the debounce, search must not have fired.
    expect(hoisted.search).not.toHaveBeenCalled()
    // After the 250ms debounce settles, the cross-category endpoint is hit.
    await waitFor(
      () => expect(hoisted.search).toHaveBeenCalledWith('wil'),
      { timeout: 2000 },
    )
  })

  it('navigates to the entry detail when a row is tapped', async () => {
    renderAt('/m/learn')
    const row = await screen.findByTestId('mlearn-entry-wilcoxon')
    fireEvent.click(row)
    await waitFor(() => {
      expect(screen.getByTestId('entry-route')).toBeTruthy()
    })
  })
})
