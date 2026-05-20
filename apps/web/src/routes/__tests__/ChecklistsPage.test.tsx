/**
 * MP20 — Vitest smoke test for the ChecklistsPage shell.
 *
 * Mounts ChecklistsPage with a fully mocked API surface and verifies that
 * all three panes render and the empty-state copy is shown when no run is
 * selected.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProjectContext } from '@/lib/projectContext'

vi.mock('@/hooks/useChecklists', () => ({
  useChecklistCatalogue: () => ({
    data: [
      {
        key: 'CONSORT_2010',
        name: 'CONSORT 2010',
        description: 'Reporting of randomised trials.',
        version: '2010',
        default_section: 'Methodology',
        item_count: 25,
      },
      {
        key: 'PRISMA_2020',
        name: 'PRISMA 2020',
        description: 'Systematic review reporting.',
        version: '2020',
        default_section: 'Methodology',
        item_count: 27,
      },
    ],
    isLoading: false,
  }),
  useChecklistRuns: () => ({ data: [], isLoading: false }),
  useChecklistRun: () => ({ data: undefined, isLoading: false }),
  useCreateChecklistRun: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  usePatchChecklistItem: () => ({ mutate: vi.fn(), isPending: false }),
  useAutoCheckRun: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteChecklistRun: () => ({ mutate: vi.fn(), isPending: false }),
}))

// react-resizable-panels uses ResizeObserver under jsdom.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
;(globalThis as unknown as {
  ResizeObserver?: typeof ResizeObserverStub
}).ResizeObserver = ResizeObserverStub

import ChecklistsPage from '../ChecklistsPage'

function wrap() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/projects/p-1/checklists']}>
        <ProjectContext.Provider value={{ projectId: 'p-1', project: null }}>
          <Routes>
            <Route
              path="/projects/:projectId/checklists"
              element={<ChecklistsPage />}
            />
          </Routes>
        </ProjectContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(cleanup)

describe('ChecklistsPage', () => {
  it('mounts the three-pane shell and shows the catalogue + empty state', () => {
    wrap()
    expect(screen.getByTestId('checklists-page-shell')).toBeDefined()
    expect(screen.getByTestId('checklists-catalogue-list')).toBeDefined()
    expect(screen.getByTestId('checklist-runs-list')).toBeDefined()
    expect(screen.getByTestId('checklists-empty-state')).toBeDefined()
    // Catalogue rows render.
    expect(screen.getByTestId('checklist-row-CONSORT_2010')).toBeDefined()
    expect(screen.getByTestId('checklist-row-PRISMA_2020')).toBeDefined()
  })

  it('catalogue rows expose a Start button per row', () => {
    wrap()
    const starts = screen.getAllByText('Start')
    expect(starts.length).toBeGreaterThanOrEqual(2)
  })
})
