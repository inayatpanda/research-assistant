import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { addMock } = vi.hoisted(() => ({ addMock: vi.fn() }))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    transformationsApi: {
      ...actual.transformationsApi,
      add: addMock,
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
})

describe('DataView — cell editing', () => {
  beforeEach(() => {
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

    // Click the (0, age) cell to begin editing.
    const cell = screen.getByTestId('cell-r-0-age')
    fireEvent.click(cell)

    const input = (await screen.findByTestId('cell-input')) as HTMLInputElement
    fireEvent.change(input, { target: { value: '99' } })
    expect(input.value).toBe('99')
    // Click the save button (Check icon).
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
    const cell = screen.getByTestId('cell-r-0-age')
    fireEvent.click(cell)
    const input = await screen.findByTestId('cell-input')
    // Press Enter without changing the value (it pre-fills to '65').
    fireEvent.keyDown(input, { key: 'Enter' })
    await new Promise((r) => setTimeout(r, 20))
    expect(addMock).not.toHaveBeenCalled()
  })
})
