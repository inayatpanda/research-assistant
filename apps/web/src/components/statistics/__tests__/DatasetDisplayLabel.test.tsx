/**
 * DEMO-FIX-C — Vitest for the display-label edit flow on DatasetDetail.
 *
 * Renders DatasetDetail with a mocked `useDataset` hook returning a
 * dataset whose first variable has a display_label, then verifies:
 *   1. The label renders in the "Display label" column.
 *   2. Clicking it switches to an Input.
 *   3. Editing + blur fires the PATCH mutation.
 *   4. The header_sanitisation_report banner renders when non-empty.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  waitFor,
} from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { Dataset } from '@/lib/api'

const { updateLabelMock } = vi.hoisted(() => ({
  updateLabelMock: vi.fn(),
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    datasetsApi: {
      ...actual.datasetsApi,
      updateVariableDisplayLabel: updateLabelMock,
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
      name: 'vas_pain_6m_postop',
      position: 0,
      inferred_type: 'numeric',
      user_type: null,
      n_missing: 0,
      sample_values: ['3', '4', '5'],
      display_label: 'VAS Pain at 6 months (post-op)',
    },
    {
      id: 'v-2',
      dataset_id: 'ds-1',
      name: 'bmi_group',
      position: 1,
      inferred_type: 'nominal',
      user_type: null,
      n_missing: 0,
      sample_values: ['Low', 'High'],
      display_label: 'BMI group',
    },
  ],
  header_sanitisation_report: [
    { original: 'VAS Pain at 6 months (post-op)', sanitised: 'vas_pain_6m_postop' },
    { original: 'BMI group', sanitised: 'bmi_group' },
  ],
}

vi.mock('@/hooks/useDatasets', async () => {
  return {
    useDataset: () => ({ data: DATASET, isLoading: false }),
    useUpdateVariableType: () => ({ mutate: vi.fn(), isPending: false }),
    useUpdateVariableDisplayLabel: () => ({
      mutate: (
        args: { variableId: string; displayLabel: string },
        opts?: { onSuccess?: () => void; onError?: (e: Error) => void },
      ) => {
        updateLabelMock(args)
        opts?.onSuccess?.()
      },
      isPending: false,
    }),
  }
})

vi.mock('@/hooks/useAnalyses', () => ({
  useAnalysesForDataset: () => ({ data: [], isLoading: false }),
}))

vi.mock('@/hooks/useTransformations', () => ({
  useTransformations: () => ({ data: [], isLoading: false }),
  useAddTransformation: () => ({ mutate: vi.fn(), isPending: false }),
  useUpdateTransformation: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteTransformation: () => ({ mutate: vi.fn(), isPending: false }),
  useReorderTransformations: () => ({ mutate: vi.fn(), isPending: false }),
}))

import { DatasetDetail } from '../DatasetDetail'

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  updateLabelMock.mockReset()
})

describe('DatasetDetail — display labels (DEMO-FIX-C)', () => {
  it('shows the sanitisation banner when header_sanitisation_report is non-empty', () => {
    const { getByTestId } = wrap(
      <DatasetDetail projectId="p-1" datasetId="ds-1" />,
    )
    const banner = getByTestId('header-sanitisation-banner')
    expect(banner.textContent ?? '').toMatch(/2 column headers/i)
  })

  it('renders the canonical name + display label side-by-side', () => {
    const { getByTestId } = wrap(
      <DatasetDetail projectId="p-1" datasetId="ds-1" />,
    )
    // Canonical name appears verbatim.
    const row1 = getByTestId('variable-row-v-1')
    expect(row1.textContent ?? '').toMatch(/vas_pain_6m_postop/)
    // Display label is shown in the editable cell.
    expect(row1.textContent ?? '').toMatch(/VAS Pain at 6 months/)
  })

  it('click-to-edit a label and blur fires the PATCH mutation', async () => {
    const { getByTestId } = wrap(
      <DatasetDetail projectId="p-1" datasetId="ds-1" />,
    )
    fireEvent.click(getByTestId('variable-label-v-2'))
    const input = getByTestId('variable-label-input-v-2') as HTMLInputElement
    expect(input).toBeDefined()
    fireEvent.change(input, { target: { value: 'BMI tertile' } })
    fireEvent.blur(input)
    await waitFor(() => {
      expect(updateLabelMock).toHaveBeenCalledWith({
        variableId: 'v-2',
        displayLabel: 'BMI tertile',
      })
    })
  })
})
