/**
 * Phase 13.5 (MP13.5) — vitest for OutputViewer.
 *
 * Mocks the analyses-related hooks so we render isolated; verifies
 * pin/unpin, expand/collapse, and the empty state.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
} from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/hooks/useAnalyses', () => ({
  useDeleteAnalysis: () => ({ mutate: vi.fn(), isPending: false }),
  useInterpretAnalysis: () => ({ mutate: vi.fn(), isPending: false }),
  usePushToManuscript: () => ({ mutate: vi.fn(), isPending: false }),
  // DEMO-FIX-C — Mock the chart-labels hook used by AnalysisResultCard.
  useUpdateChartLabels: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock('@/hooks/useAnalysisPlans', () => ({
  useCreateAnalysisPlan: () => ({ mutate: vi.fn(), isPending: false }),
}))

import type { Analysis, Dataset } from '@/lib/api'
import { OutputViewer } from '../OutputViewer'

const DATASET: Dataset = {
  id: 'ds-1',
  project_id: 'p-1',
  filename: 'd.csv',
  file_type: 'csv',
  n_rows: 10,
  n_columns: 1,
  created_at: '2026-05-18T00:00:00Z',
  variables: [
    {
      id: 'v-1',
      dataset_id: 'ds-1',
      name: 'x',
      position: 0,
      inferred_type: 'numeric',
      user_type: null,
      n_missing: 0,
      sample_values: ['1'],
    },
  ],
}

function makeAnalysis(id: string, created_at: string): Analysis {
  return {
    id,
    project_id: 'p-1',
    dataset_id: 'ds-1',
    question_type: 'group_comparison',
    chosen_test: 'independent_t',
    recommendation_rationale: 'r',
    variables: {},
    status: 'completed',
    created_at,
    result: {
      summary: { p_value: 0.04 },
      assumptions: {},
      chart: null,
      ai_interpretation: null,
    },
  }
}

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={client}>{node}</QueryClientProvider>
    </MemoryRouter>,
  )
}

afterEach(() => {
  cleanup()
  // Wipe per-dataset state between tests.
  if (typeof localStorage !== 'undefined') {
    try {
      localStorage.clear()
    } catch {
      /* ignore */
    }
  }
})

describe('OutputViewer', () => {
  it('renders the empty state when no analyses', () => {
    wrap(<OutputViewer projectId="p-1" dataset={DATASET} analyses={[]} />)
    expect(screen.getByTestId('output-viewer-empty')).toBeTruthy()
  })

  it('renders all analyses in newest-first order', () => {
    const a = [
      makeAnalysis('a-old', '2026-05-17T00:00:00Z'),
      makeAnalysis('a-new', '2026-05-18T00:00:00Z'),
    ]
    wrap(<OutputViewer projectId="p-1" dataset={DATASET} analyses={a} />)
    const rows = screen.getAllByTestId(/output-row-/)
    expect(rows).toHaveLength(2)
    expect(rows[0].getAttribute('data-testid')).toBe('output-row-a-new')
  })

  it('toggles a card collapsed', () => {
    const a = [makeAnalysis('a-1', '2026-05-18T00:00:00Z')]
    wrap(<OutputViewer projectId="p-1" dataset={DATASET} analyses={a} />)
    // Initially expanded → both the OutputViewer row header AND the inner
    // AnalysisResultCard show the test label (2 occurrences).
    expect(screen.getAllByText(/Independent t-test/i).length).toBe(2)
    fireEvent.click(screen.getByTestId('output-toggle-a-1'))
    // After collapse, only the row header label remains (1 occurrence).
    expect(screen.getAllByText(/Independent t-test/i).length).toBe(1)
  })

  it('pins an analysis to the top', () => {
    const a = [
      makeAnalysis('a-old', '2026-05-17T00:00:00Z'),
      makeAnalysis('a-new', '2026-05-18T00:00:00Z'),
    ]
    wrap(<OutputViewer projectId="p-1" dataset={DATASET} analyses={a} />)
    fireEvent.click(screen.getByTestId('output-pin-a-old'))
    const rows = screen.getAllByTestId(/output-row-/)
    // pinned 'a-old' should now appear first
    expect(rows[0].getAttribute('data-testid')).toBe('output-row-a-old')
  })
})
