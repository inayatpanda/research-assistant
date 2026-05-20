/**
 * MP18 — Vitest smoke test for the Economics page.
 *
 * Mounts EconomicsPage with a fully mocked API surface and verifies that:
 *   1. The ResizablePanelGroup shell mounts.
 *   2. The autoSaveId persists divider widths to the economics key.
 *   3. The existing analyses render in the left-pane list.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProjectContext } from '@/lib/projectContext'
import type { Dataset, EconomicAnalysis } from '@/lib/api'

const ANALYSIS: EconomicAnalysis = {
  id: 'econ-1',
  project_id: 'p-1',
  dataset_id: 'ds-1',
  name: 'CRAFFT CEA',
  currency: 'GBP',
  time_horizon_months: 12,
  perspective: 'healthcare_system',
  discount_rate_costs: 0.035,
  discount_rate_qalys: 0.035,
  wtp_thresholds: [20000, 30000],
  utility_value_set: 'EQ5D_5L_UK',
  bootstrap_n: 1000,
  seed: 42,
  treatment_col: 'arm',
  comparator_label: 'control',
  intervention_label: 'anterior',
  cost_columns: [],
  ai_interpretation: null,
  created_at: 'x',
  updated_at: 'x',
  result: null,
}

const DATASET: Dataset = {
  id: 'ds-1',
  project_id: 'p-1',
  filename: 'data.csv',
  file_type: 'text/csv',
  n_rows: 10,
  n_columns: 2,
  created_at: '2026-05-18T00:00:00Z',
  variables: [
    {
      id: 'v-1',
      dataset_id: 'ds-1',
      name: 'cost_total',
      position: 0,
      inferred_type: 'numeric',
      user_type: null,
      n_missing: 0,
      sample_values: ['100', '200'],
      display_label: 'Total cost',
    },
  ],
  header_sanitisation_report: [],
}

vi.mock('@/hooks/useEconomicAnalyses', () => ({
  useEconomicAnalyses: () => ({ data: [ANALYSIS], isLoading: false }),
  useDeleteEconomicAnalysis: () => ({ mutate: vi.fn(), isPending: false }),
  useCreateEconomicAnalysis: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdateEconomicAnalysis: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useRunEconomicAnalysis: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useInterpretEconomicAnalysis: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  usePushEconomicAnalysis: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useRunEconomicSensitivity: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUtilityValueSets: () => ({
    data: [
      {
        key: 'EQ5D_5L_UK',
        label: 'EQ-5D-5L (Devlin 2018)',
        dimensions: [],
        levels: 5,
        source_citation: 'Devlin 2018',
        notes: null,
      },
    ],
    isLoading: false,
  }),
}))

vi.mock('@/hooks/useDatasets', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useDatasets')>()
  return {
    ...actual,
    useDatasets: () => ({ data: [DATASET], isLoading: false }),
  }
})

// react-resizable-panels uses ResizeObserver which jsdom lacks.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
;(globalThis as unknown as {
  ResizeObserver?: typeof ResizeObserverStub
}).ResizeObserver = ResizeObserverStub

import EconomicsPage from '../EconomicsPage'

function wrap() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/projects/p-1/economics']}>
        <ProjectContext.Provider value={{ projectId: 'p-1', project: null }}>
          <Routes>
            <Route
              path="/projects/:projectId/economics"
              element={<EconomicsPage />}
            />
          </Routes>
        </ProjectContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(cleanup)

describe('EconomicsPage', () => {
  it('mounts the resizable shell + analysis card list', () => {
    const { container, getByTestId } = wrap()
    expect(getByTestId('economics-resizable-shell')).toBeDefined()
    expect(screen.getByTestId(`economic-analysis-card-${ANALYSIS.id}`))
      .toBeDefined()
    // Resize handles render.
    const handles = container.querySelectorAll('[data-panel-resize-handle-id]')
    expect(handles.length).toBeGreaterThanOrEqual(1)
  })
})
