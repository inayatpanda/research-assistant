/**
 * Statistics layout refactor — Vitest for the StatisticsPage shell after the
 * left/right rails were collapsed into a full-width dataset view with a
 * horizontal data toolbar.
 *
 * Verifies:
 *   1. The page shell wrapper renders (without a ResizablePanelGroup).
 *   2. The new horizontal DatasetToolbar mounts with Upload / PSM / New analysis.
 *   3. The page-level toolbar still surfaces all four project-scoped tools.
 *   4. The full-width tab strip from DatasetDetail is reachable.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Dataset } from '@/lib/api'
import { ProjectContext } from '@/lib/projectContext'

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    projectsApi: {
      ...actual.projectsApi,
      get: vi.fn(async () => ({
        id: 'p-1',
        title: 'Demo Project',
        study_type: 'RCT',
        template_journal: null,
      })),
    },
    statsReportApi: {
      ...actual.statsReportApi,
      export: vi.fn(),
    },
  }
})

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
      name: 'age',
      position: 0,
      inferred_type: 'numeric',
      user_type: null,
      n_missing: 0,
      sample_values: ['30', '40', '50'],
      display_label: 'Age',
    },
  ],
  header_sanitisation_report: [],
}

vi.mock('@/hooks/useDatasets', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useDatasets')>()
  return {
    ...actual,
    useDatasets: () => ({ data: [DATASET], isLoading: false }),
    useDataset: () => ({ data: DATASET, isLoading: false }),
    useUploadDataset: () => ({ mutate: vi.fn(), isPending: false }),
    useDeleteDataset: () => ({ mutate: vi.fn(), isPending: false }),
    useUpdateVariableType: () => ({ mutate: vi.fn(), isPending: false }),
    useUpdateVariableDisplayLabel: () => ({
      mutate: vi.fn(),
      isPending: false,
    }),
  }
})

vi.mock('@/hooks/useAnalyses', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useAnalyses')>()
  return {
    ...actual,
    useAnalysesForDataset: () => ({ data: [], isLoading: false }),
  }
})

vi.mock('@/hooks/useTransformations', async (importOriginal) => {
  const actual = await importOriginal<
    typeof import('@/hooks/useTransformations')
  >()
  return {
    ...actual,
    useTransformations: () => ({ data: [], isLoading: false }),
    useAddTransformation: () => ({ mutate: vi.fn(), isPending: false }),
    useUpdateTransformation: () => ({ mutate: vi.fn(), isPending: false }),
    useDeleteTransformation: () => ({ mutate: vi.fn(), isPending: false }),
    useReorderTransformations: () => ({ mutate: vi.fn(), isPending: false }),
  }
})

// jsdom doesn't ship ResizeObserver; some libs (recharts, radix popovers used
// by Select) probe for it during render.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
;(globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub })
  .ResizeObserver = ResizeObserverStub

import StatisticsPage from '../StatisticsPage'

function wrap() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/projects/p-1/statistics']}>
        <ProjectContext.Provider value={{ projectId: 'p-1', project: null }}>
          <Routes>
            <Route
              path="/projects/:projectId/statistics"
              element={<StatisticsPage />}
            />
          </Routes>
        </ProjectContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(cleanup)

describe('StatisticsPage — full-width layout', () => {
  it('mounts the page shell without a ResizablePanelGroup', () => {
    const { getByTestId, container } = wrap()
    expect(getByTestId('statistics-page-shell')).toBeDefined()
    // The old left/right rail group should no longer be present.
    expect(container.querySelector('[data-panel-group-id]')).toBeNull()
    expect(
      container.querySelector('[data-panel-resize-handle-id]'),
    ).toBeNull()
  })

  it('renders the horizontal dataset toolbar with Upload, PSM and New analysis', () => {
    const { getByTestId } = wrap()
    expect(getByTestId('dataset-toolbar')).toBeDefined()
    expect(getByTestId('dataset-toolbar-upload')).toBeDefined()
    expect(getByTestId('dataset-toolbar-psm')).toBeDefined()
    expect(getByTestId('dataset-toolbar-new-analysis')).toBeDefined()
  })

  it('shows all four project-scoped tool buttons in the page toolbar', () => {
    const { getByTestId } = wrap()
    expect(getByTestId('open-cross-dataset')).toBeDefined()
    expect(getByTestId('open-power-calculator')).toBeDefined()
    expect(getByTestId('open-analysis-plans')).toBeDefined()
    expect(getByTestId('export-stats-report')).toBeDefined()
  })

  it('mounts the full-width DatasetDetail tab strip below the toolbar', () => {
    const { getByTestId } = wrap()
    expect(getByTestId('dataset-detail-tabs')).toBeDefined()
  })
})
