/**
 * Phase M5.2 — MobileChecklists smoke tests.
 *
 *   1. The catalogue list renders one row per checklist type.
 *   2. Tapping a type navigates to /m/checklists/:type and loads its
 *      items into the detail view.
 *   3. Tapping an item triggers a status-PATCH on the backend.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const hoisted = vi.hoisted(() => ({
  projects: [
    {
      id: 'p-1',
      user_id: 'u-1',
      title: 'Outcome study',
      study_type: 'Outcome Study',
      citation_style: 'vancouver' as const,
      ai_provider: 'gemini' as const,
      target_journal: null,
      prospero_number: null,
      clinicaltrials_number: null,
      template_journal: null,
      inline_citation_mode: 'bracket_numeric' as const,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ],
  catalogue: [
    {
      key: 'CONSORT_2010',
      name: 'CONSORT 2010',
      description: 'Trials',
      version: '2010',
      default_section: 'Methods',
      item_count: 25,
    },
    {
      key: 'PRISMA_2020',
      name: 'PRISMA 2020',
      description: 'SR',
      version: '2020',
      default_section: 'Methods',
      item_count: 27,
    },
  ],
  catalogueDetail: {
    key: 'CONSORT_2010',
    name: 'CONSORT 2010',
    description: 'Trials',
    version: '2010',
    default_section: 'Methods',
    items: [],
  },
  runs: [] as Array<unknown>,
  run: {
    id: 'run-1',
    project_id: 'p-1',
    checklist_key: 'CONSORT_2010',
    title: 'CONSORT 2010',
    items: [
      {
        item_id: '1a',
        item_text: 'Identification as a randomised trial in the title.',
        status: 'unclear' as const,
        comment: '',
        mapped_section: null,
        mapped_text_excerpt: null,
      },
    ],
    overall_compliance_pct: 0,
    created_at: '2026-05-21T00:00:00Z',
    updated_at: '2026-05-21T00:00:00Z',
  },
  createRun: vi.fn(),
  getRun: vi.fn(),
  patchItem: vi.fn(),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  hoisted.createRun.mockResolvedValue(hoisted.run)
  hoisted.getRun.mockResolvedValue(hoisted.run)
  hoisted.patchItem.mockImplementation(async (_pid, _rid, itemId, patch) => ({
    ...hoisted.run,
    items: hoisted.run.items.map((i) =>
      i.item_id === itemId ? { ...i, ...patch } : i,
    ),
  }))
  return {
    ...actual,
    projectsApi: { list: vi.fn(async () => hoisted.projects) },
    checklistsApi: {
      listCatalogue: vi.fn(async () => hoisted.catalogue),
      getCatalogue: vi.fn(async () => hoisted.catalogueDetail),
      listRuns: vi.fn(async () => hoisted.runs),
      createRun: hoisted.createRun,
      getRun: hoisted.getRun,
      patchItem: hoisted.patchItem,
    },
  }
})

// Bypass the IDB cache layer.
vi.mock('@/mobile/lib/offlineLearn', async () => ({
  cacheable: async (_key: string, fetcher: () => Promise<unknown>) => ({
    data: await fetcher(),
    offline: false,
  }),
  entryKey: (c: string, s: string) => `${c}:${s}`,
  listKey: (c: string) => `__list:${c}`,
}))

import MobileChecklistDetail from '@/mobile/pages/MobileChecklistDetail'
import MobileChecklists from '@/mobile/pages/MobileChecklists'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/m/checklists" element={<MobileChecklists />} />
          <Route
            path="/m/checklists/:type"
            element={<MobileChecklistDetail />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  window.localStorage?.clear?.()
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('MobileChecklists', () => {
  it('renders the catalogue list with available types', async () => {
    renderAt('/m/checklists')
    await waitFor(() => {
      expect(screen.getByTestId('mchecklists-type-CONSORT_2010')).toBeTruthy()
      expect(screen.getByTestId('mchecklists-type-PRISMA_2020')).toBeTruthy()
    })
  })

  it('navigates to the detail page on tap', async () => {
    renderAt('/m/checklists')
    await waitFor(() => screen.getByTestId('mchecklists-type-CONSORT_2010'))
    fireEvent.click(screen.getByTestId('mchecklists-type-CONSORT_2010'))
    await waitFor(() => {
      expect(screen.getByTestId('mchecklists-items')).toBeTruthy()
      expect(screen.getByTestId('mchecklists-item-1a')).toBeTruthy()
    })
  })

  it('PATCHes the item status when an item row is tapped', async () => {
    renderAt('/m/checklists/CONSORT_2010')
    await waitFor(() => screen.getByTestId('mchecklists-item-1a'))
    fireEvent.click(screen.getByTestId('mchecklists-item-1a'))
    await waitFor(() => {
      expect(hoisted.patchItem).toHaveBeenCalled()
    })
    // Cycle starts at 'unclear' so cycleStatus returns 'fail'.
    const lastCall =
      hoisted.patchItem.mock.calls[hoisted.patchItem.mock.calls.length - 1]
    expect(lastCall[3]).toEqual({ status: 'fail' })
  })
})
