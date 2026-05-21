/**
 * Phase M4.4 — MobileStatsConfigure smoke tests.
 *
 *   1. The form renders the right column-picker rows for the chosen
 *      analysis type (t-test → outcome + group).
 *   2. Filling the pickers + tapping "Run analysis" triggers the
 *      analyses create + run mutations.
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
import { afterEach, describe, expect, it, vi } from 'vitest'

const hoisted = vi.hoisted(() => ({
  create: vi.fn(async () => ({
    id: 'a-1',
    project_id: 'p-1',
    dataset_id: 'ds-1',
    question_type: 'group_comparison' as const,
    chosen_test: 'independent_t' as const,
    recommendation_rationale: '',
    variables: {},
    status: 'ready' as const,
    created_at: '2026-05-21T00:00:00Z',
  })),
  run: vi.fn(async () => ({
    id: 'a-1',
    project_id: 'p-1',
    dataset_id: 'ds-1',
    question_type: 'group_comparison' as const,
    chosen_test: 'independent_t' as const,
    recommendation_rationale: '',
    variables: {},
    status: 'completed' as const,
    created_at: '2026-05-21T00:00:00Z',
  })),
  interpret: vi.fn(async () => ({
    id: 'a-1',
    project_id: 'p-1',
    dataset_id: 'ds-1',
    question_type: 'group_comparison' as const,
    chosen_test: 'independent_t' as const,
    recommendation_rationale: '',
    variables: {},
    status: 'completed' as const,
    created_at: '2026-05-21T00:00:00Z',
  })),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  return {
    ...actual,
    projectsApi: {
      list: vi.fn(async () => [
        {
          id: 'p-1',
          user_id: 'u-1',
          title: 'Outcome study',
          study_type: 'Outcome Study',
          citation_style: 'vancouver',
          ai_provider: 'gemini',
          target_journal: null,
          prospero_number: null,
          clinicaltrials_number: null,
          template_journal: null,
          inline_citation_mode: 'bracket_numeric',
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ]),
    },
    datasetsApi: {
      list: vi.fn(),
      get: vi.fn(async () => ({
        id: 'ds-1',
        project_id: 'p-1',
        filename: 'masterchart.csv',
        file_type: 'csv',
        n_rows: 120,
        n_columns: 2,
        created_at: '2026-05-01T00:00:00Z',
        variables: [
          {
            id: 'v-1',
            dataset_id: 'ds-1',
            name: 'age',
            position: 0,
            inferred_type: 'numeric',
            user_type: 'numeric',
            n_missing: 0,
            sample_values: ['42'],
            display_label: 'Age',
          },
          {
            id: 'v-2',
            dataset_id: 'ds-1',
            name: 'sex',
            position: 1,
            inferred_type: 'nominal',
            user_type: 'nominal',
            n_missing: 0,
            sample_values: ['M'],
            display_label: 'Sex',
          },
        ],
        derived_from_dataset_id: null,
        derived_from_dataset_ids: null,
        dataset_metadata: null,
        header_sanitisation_report: [],
      })),
      preview: vi.fn(),
      upload: vi.fn(),
      delete: vi.fn(),
      updateVariable: vi.fn(),
      updateVariableDisplayLabel: vi.fn(),
    },
    analysesApi: {
      create: hoisted.create,
      run: hoisted.run,
      interpret: hoisted.interpret,
      get: vi.fn(),
      delete: vi.fn(),
      listForDataset: vi.fn(),
      recommend: vi.fn(),
      pushToManuscript: vi.fn(),
      updateChartLabels: vi.fn(),
    },
  }
})

import MobileStatsConfigure from '@/mobile/pages/MobileStatsConfigure'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            path="/m/stats/:datasetId/configure/:analysisType"
            element={<MobileStatsConfigure />}
          />
          <Route
            path="/m/stats/:datasetId/results/:analysisId"
            element={<div data-testid="results-route">results</div>}
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

describe('MobileStatsConfigure', () => {
  it('renders the t-test form with outcome + group picker rows', async () => {
    renderAt('/m/stats/ds-1/configure/t_test')
    await waitFor(() => {
      expect(screen.getByTestId('mstats-pick-outcome')).toBeTruthy()
      expect(screen.getByTestId('mstats-pick-groups')).toBeTruthy()
      expect(screen.getByTestId('mstats-configure-run')).toBeTruthy()
    })
  })

  it('runs the analysis end-to-end and navigates to results', async () => {
    renderAt('/m/stats/ds-1/configure/t_test')
    await waitFor(() => screen.getByTestId('mstats-pick-outcome'))

    // Outcome picker → tap "age".
    fireEvent.click(screen.getByTestId('mstats-pick-outcome'))
    await waitFor(() => screen.getByTestId('mstats-picker-age'))
    fireEvent.click(screen.getByTestId('mstats-picker-age'))

    // Groups picker → tap "sex".
    await waitFor(() => screen.getByTestId('mstats-pick-groups'))
    fireEvent.click(screen.getByTestId('mstats-pick-groups'))
    await waitFor(() => screen.getByTestId('mstats-picker-sex'))
    fireEvent.click(screen.getByTestId('mstats-picker-sex'))

    fireEvent.click(screen.getByTestId('mstats-configure-run'))
    await waitFor(() => expect(hoisted.create).toHaveBeenCalled())
    await waitFor(() => expect(hoisted.run).toHaveBeenCalled())
    await waitFor(() =>
      expect(screen.getByTestId('results-route')).toBeTruthy(),
    )
  })
})
