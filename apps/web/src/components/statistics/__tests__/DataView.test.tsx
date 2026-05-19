import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { addMock, previewMock } = vi.hoisted(() => ({
  addMock: vi.fn(),
  previewMock: vi.fn(),
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    transformationsApi: {
      ...actual.transformationsApi,
      add: addMock,
    },
    datasetsApi: {
      ...actual.datasetsApi,
      preview: previewMock,
    },
  }
})

import type { Dataset } from '@/lib/api'
import { DataView } from '../DataView'

const DATASET: Dataset = {
  id: 'ds-1',
  project_id: 'p-1',
  filename: 'cohort.csv',
  file_type: 'csv',
  n_rows: 3,
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
      sample_values: ['65', '72', '58'],
    },
    {
      id: 'v-2',
      dataset_id: 'ds-1',
      name: 'bmi',
      position: 1,
      inferred_type: 'numeric',
      user_type: null,
      n_missing: 0,
      sample_values: ['25.1', '28.4', '22.0'],
    },
  ],
}

const PREVIEW_PAYLOAD = {
  columns: ['age', 'bmi'],
  rows: [
    { __row_index: 0, age: 65, bmi: 25.1 },
    { __row_index: 1, age: 72, bmi: 28.4 },
    { __row_index: 2, age: 58, bmi: 22.0 },
  ],
  offset: 0,
  limit: 50,
  total: 3,
}

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  addMock.mockReset()
  previewMock.mockReset()
})

describe('DataView — cell editing', () => {
  beforeEach(() => {
    previewMock.mockResolvedValue(PREVIEW_PAYLOAD)
    addMock.mockResolvedValue({
      id: 'tx-new',
      dataset_id: 'ds-1',
      position: 0,
      op_type: 'mutate',
      op_args: {},
      label: '',
      created_at: '2026-05-18T00:00:00Z',
    })
  })

  it('emits a mutate op into the transformation stack on cell save', async () => {
    wrap(<DataView projectId="p-1" dataset={DATASET} />)

    // Wait for the preview to load and the (0, age) cell to render.
    const cell = await screen.findByTestId('cell-r-0-age')
    fireEvent.click(cell)

    const input = (await screen.findByTestId(
      'cell-input',
      {},
      { timeout: 2000 },
    )) as HTMLInputElement
    fireEvent.change(input, { target: { value: '99' } })
    expect(input.value).toBe('99')
    fireEvent.click(screen.getByLabelText('Save edit'))

    await waitFor(() => expect(addMock).toHaveBeenCalledTimes(1))
    const [, , body] = addMock.mock.calls[0]
    expect(body.op_type).toBe('mutate')
    expect(body.op_args.column).toBe('age')
    expect(body.op_args.expr).toBe('99')
    expect(body.op_args.where.prev).toBe('65')
  })

  it('does NOT emit an op when the edited value is unchanged', async () => {
    wrap(<DataView projectId="p-1" dataset={DATASET} />)
    const cell = await screen.findByTestId('cell-r-0-age')
    fireEvent.click(cell)
    const input = await screen.findByTestId('cell-input')
    fireEvent.keyDown(input, { key: 'Enter' })
    await new Promise((r) => setTimeout(r, 20))
    expect(addMock).not.toHaveBeenCalled()
  })

  it('renders the actual row count from the preview endpoint', async () => {
    // Even though dataset.n_rows says 3, the preview is the source of truth.
    previewMock.mockResolvedValue({
      ...PREVIEW_PAYLOAD,
      total: 120,
    })
    wrap(<DataView projectId="p-1" dataset={{ ...DATASET, n_rows: 120 }} />)
    await screen.findByTestId('cell-r-0-age')
    expect(
      screen.getByText(/of 120 rows/i, { exact: false }),
    ).toBeTruthy()
  })

  it('shows a friendly empty state when the dataset has zero rows', async () => {
    previewMock.mockResolvedValue({
      columns: ['age', 'bmi'],
      rows: [],
      offset: 0,
      limit: 50,
      total: 0,
    })
    wrap(<DataView projectId="p-1" dataset={{ ...DATASET, n_rows: 0 }} />)
    await waitFor(() =>
      expect(screen.queryByText(/dataset has no rows/i)).toBeTruthy(),
    )
  })
})
