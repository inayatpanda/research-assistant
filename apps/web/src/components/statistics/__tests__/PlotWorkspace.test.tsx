/**
 * Phase 13.5 (MP13.5) — vitest for PlotWorkspace.
 *
 * Mocks the plotsApi to assert the form picks the right channels for each
 * geom and that the saved-plot list is rendered from the query result.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'

beforeAll(() => {
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = vi.fn()
  }
  if (!('hasPointerCapture' in Element.prototype)) {
    Element.prototype.hasPointerCapture = vi.fn(() => false)
    Element.prototype.releasePointerCapture = vi.fn()
  }
})

const { listMock, createMock, deleteMock, regenMock } = vi.hoisted(() => ({
  listMock: vi.fn(),
  createMock: vi.fn(),
  deleteMock: vi.fn(),
  regenMock: vi.fn(),
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    plotsApi: {
      list: listMock,
      create: createMock,
      delete: deleteMock,
      regenerate: regenMock,
    },
  }
})

import type { Dataset } from '@/lib/api'
import { PlotWorkspace } from '../PlotWorkspace'

const DATASET: Dataset = {
  id: 'ds-1',
  project_id: 'p-1',
  filename: 'd.csv',
  file_type: 'csv',
  n_rows: 12,
  n_columns: 2,
  created_at: '2026-05-18T00:00:00Z',
  variables: [
    {
      id: 'v-1',
      dataset_id: 'ds-1',
      name: 'score',
      position: 0,
      inferred_type: 'numeric',
      user_type: null,
      n_missing: 0,
      sample_values: ['10', '12'],
    },
    {
      id: 'v-2',
      dataset_id: 'ds-1',
      name: 'group',
      position: 1,
      inferred_type: 'nominal',
      user_type: null,
      n_missing: 0,
      sample_values: ['A', 'B'],
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
  listMock.mockReset()
  createMock.mockReset()
  deleteMock.mockReset()
  regenMock.mockReset()
})

describe('PlotWorkspace', () => {
  beforeEach(() => {
    listMock.mockResolvedValue([])
  })

  it('renders the builder and empty-state when no plots exist', async () => {
    wrap(<PlotWorkspace projectId="p-1" dataset={DATASET} />)
    expect(screen.getByTestId('plot-workspace')).toBeTruthy()
    await waitFor(() =>
      expect(screen.getByText(/No plots yet/i)).toBeTruthy(),
    )
  })

  it('renders saved plots from the query result', async () => {
    listMock.mockResolvedValue([
      {
        id: 'plot-1',
        project_id: 'p-1',
        dataset_id: 'ds-1',
        title: 'My histogram',
        spec: { geom: 'histogram', x: 'score' },
        png_data_uri: 'data:image/png;base64,AAAA',
        created_at: '2026-05-18T00:00:00Z',
        updated_at: '2026-05-18T00:00:00Z',
      },
    ])
    wrap(<PlotWorkspace projectId="p-1" dataset={DATASET} />)
    await waitFor(() =>
      expect(screen.getByTestId('plot-row-plot-1')).toBeTruthy(),
    )
    expect(screen.getByText('My histogram')).toBeTruthy()
  })

  it('refuses to save when a required channel is empty', async () => {
    wrap(<PlotWorkspace projectId="p-1" dataset={DATASET} />)
    await waitFor(() => expect(listMock).toHaveBeenCalled())
    fireEvent.click(screen.getByTestId('plot-save'))
    // create not called — x is empty
    expect(createMock).not.toHaveBeenCalled()
  })
})
