/**
 * Phase M4.2 — MobileStatsPreview smoke tests.
 *
 *   1. Summary chip row + mini-table render with the dataset's columns.
 *   2. Tapping a column header opens the type sheet; picking a type +
 *      saving calls ``datasetsApi.updateVariable``.
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
  updateVariable: vi.fn(async () => ({
    id: 'v-1',
    dataset_id: 'ds-1',
    name: 'age',
    position: 0,
    inferred_type: 'numeric' as const,
    user_type: 'numeric' as const,
    n_missing: 0,
    sample_values: ['42'],
    display_label: 'Age',
  })),
  updateLabel: vi.fn(async () => ({
    id: 'v-1',
    dataset_id: 'ds-1',
    name: 'age',
    position: 0,
    inferred_type: 'numeric' as const,
    user_type: null,
    n_missing: 0,
    sample_values: ['42'],
    display_label: 'Age',
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
            user_type: null,
            n_missing: 0,
            sample_values: ['42'],
            display_label: null,
          },
          {
            id: 'v-2',
            dataset_id: 'ds-1',
            name: 'sex',
            position: 1,
            inferred_type: 'nominal',
            user_type: null,
            n_missing: 0,
            sample_values: ['M'],
            display_label: null,
          },
        ],
        derived_from_dataset_id: null,
        derived_from_dataset_ids: null,
        dataset_metadata: null,
        header_sanitisation_report: [],
      })),
      preview: vi.fn(async () => ({
        columns: ['age', 'sex'],
        rows: [
          { __row_index: 0, age: 42, sex: 'M' },
          { __row_index: 1, age: 38, sex: 'F' },
        ],
        offset: 0,
        limit: 8,
        total: 120,
      })),
      upload: vi.fn(),
      delete: vi.fn(),
      updateVariable: hoisted.updateVariable,
      updateVariableDisplayLabel: hoisted.updateLabel,
    },
  }
})

import MobileStatsPreview from '@/mobile/pages/MobileStatsPreview'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            path="/m/stats/:datasetId/preview"
            element={<MobileStatsPreview />}
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

describe('MobileStatsPreview', () => {
  it('renders summary chips + the mini-table', async () => {
    renderAt('/m/stats/ds-1/preview')
    await waitFor(() => {
      expect(screen.getByTestId('mstats-summary-rows').textContent).toContain('120')
      expect(screen.getByTestId('mstats-summary-cols').textContent).toContain('2')
      expect(screen.getByTestId('mstats-preview-table')).toBeTruthy()
      expect(screen.getByTestId('mstats-col-v-1')).toBeTruthy()
    })
  })

  it('opens the type sheet on header tap and saves the chosen type', async () => {
    renderAt('/m/stats/ds-1/preview')
    await waitFor(() => screen.getByTestId('mstats-col-v-1'))
    fireEvent.click(screen.getByTestId('mstats-col-v-1'))
    await waitFor(() =>
      expect(screen.getByTestId('mstats-col-type-numeric')).toBeTruthy(),
    )
    fireEvent.click(screen.getByTestId('mstats-col-type-numeric'))
    fireEvent.click(screen.getByTestId('mstats-col-save'))
    await waitFor(() =>
      expect(hoisted.updateVariable).toHaveBeenCalledWith(
        'p-1',
        'ds-1',
        'v-1',
        'numeric',
      ),
    )
  })
})
