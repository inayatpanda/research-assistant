/**
 * DEMO-FIX-B — Vitest for the collapsible right-rail blocks (Transformations,
 * Show syntax) on DatasetDetail. Verifies:
 *   1. Both blocks render expanded by default.
 *   2. Clicking the chevron toggle hides the body.
 *   3. Collapsed state is persisted under
 *      `dataset-<id>-blocks-collapsed` in localStorage.
 *   4. State is per-dataset (different datasetId → independent storage).
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Dataset } from '@/lib/api'

// vitest 4 + jsdom 29 don't ship a working localStorage by default. Provide a
// minimal in-memory shim so the persistence assertions below run.
function installLocalStorageShim() {
  const store = new Map<string, string>()
  const shim: Storage = {
    get length() {
      return store.size
    },
    clear: () => store.clear(),
    getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
    key: (i: number) => Array.from(store.keys())[i] ?? null,
    removeItem: (k: string) => {
      store.delete(k)
    },
    setItem: (k: string, v: string) => {
      store.set(k, String(v))
    },
  }
  Object.defineProperty(window, 'localStorage', {
    value: shim,
    configurable: true,
    writable: true,
  })
  // Also expose on globalThis so bare `localStorage` references resolve.
  Object.defineProperty(globalThis, 'localStorage', {
    value: shim,
    configurable: true,
    writable: true,
  })
}
installLocalStorageShim()

const DATASET: Dataset = {
  id: 'ds-A',
  project_id: 'p-1',
  filename: 'data.csv',
  file_type: 'text/csv',
  n_rows: 10,
  n_columns: 2,
  created_at: '2026-05-18T00:00:00Z',
  variables: [
    {
      id: 'v-1',
      dataset_id: 'ds-A',
      name: 'age',
      position: 0,
      inferred_type: 'numeric',
      user_type: null,
      n_missing: 0,
      sample_values: ['30'],
      display_label: 'Age',
    },
  ],
  header_sanitisation_report: [],
}

vi.mock('@/hooks/useDatasets', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/useDatasets')>()
  return {
    ...actual,
    useDataset: () => ({ data: DATASET, isLoading: false }),
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

beforeEach(() => {
  try {
    window.localStorage.clear()
  } catch {
    /* jsdom localStorage is always available */
  }
})
afterEach(cleanup)

describe('DatasetDetail — collapsible blocks (DEMO-FIX-B)', () => {
  it('renders both collapsible sections expanded by default', () => {
    const { getByTestId } = wrap(
      <DatasetDetail
        projectId="p-1"
        datasetId="ds-A"
        onNewAnalysis={() => {}}
      />,
    )
    expect(getByTestId('collapsible-transformations')).toBeDefined()
    expect(getByTestId('collapsible-syntax')).toBeDefined()
    // Bodies render while expanded.
    expect(getByTestId('collapsible-body-transformations')).toBeDefined()
    expect(getByTestId('collapsible-body-syntax')).toBeDefined()
  })

  it('clicking the Transformations toggle hides the body and persists state', () => {
    const { getByTestId, queryByTestId } = wrap(
      <DatasetDetail
        projectId="p-1"
        datasetId="ds-A"
        onNewAnalysis={() => {}}
      />,
    )
    const toggle = getByTestId('collapsible-toggle-transformations')
    fireEvent.click(toggle)
    expect(queryByTestId('collapsible-body-transformations')).toBeNull()
    // localStorage now reflects the collapsed flag.
    const raw = window.localStorage.getItem('dataset-ds-A-blocks-collapsed')
    expect(raw).not.toBeNull()
    expect(JSON.parse(raw!)).toMatchObject({ transformations: true })
  })

  it('restores collapsed state from localStorage on mount', () => {
    window.localStorage.setItem(
      'dataset-ds-A-blocks-collapsed',
      JSON.stringify({ transformations: true, syntax: true }),
    )
    const { queryByTestId } = wrap(
      <DatasetDetail
        projectId="p-1"
        datasetId="ds-A"
        onNewAnalysis={() => {}}
      />,
    )
    expect(queryByTestId('collapsible-body-transformations')).toBeNull()
    expect(queryByTestId('collapsible-body-syntax')).toBeNull()
  })
})
