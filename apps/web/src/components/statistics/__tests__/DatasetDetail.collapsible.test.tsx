/**
 * Statistics layout refactor — Vitest for the new tab-based DatasetDetail.
 *
 * The previous demo-fix-B placed Transformations and Syntax in a collapsible
 * right rail. After the layout refactor those blocks live as dedicated tabs
 * alongside Variables / Data view / Plots / Diagnostics. The right rail and
 * its localStorage-backed collapse state are gone. These tests verify:
 *   1. All six tabs render in the tab strip.
 *   2. Variables tab is active on initial render (content visible by default).
 *   3. Clicking the Transformations tab switches the active panel.
 *   4. Clicking the Syntax tab mounts the syntax renderer.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { Dataset } from '@/lib/api'

// vitest 4 + jsdom 29 don't ship a working localStorage by default. Provide a
// minimal in-memory shim so anything reading localStorage doesn't throw.
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
    /* shim cleared above; ignore */
  }
})
afterEach(cleanup)

describe('DatasetDetail — tabbed layout', () => {
  it('renders the six tabs in the dataset tab strip', () => {
    const { getByTestId, getByRole } = wrap(
      <DatasetDetail projectId="p-1" datasetId="ds-A" />,
    )
    const tabs = getByTestId('dataset-detail-tabs')
    expect(tabs).toBeDefined()
    // All six tabs are reachable by accessible name.
    for (const label of [
      'Variables',
      'Data view',
      'Plots',
      'Diagnostics',
      'Transformations',
      'Syntax',
    ]) {
      expect(getByRole('tab', { name: new RegExp(label, 'i') })).toBeDefined()
    }
  })

  it('defaults to the Variables tab on initial mount', () => {
    const { getByTestId } = wrap(
      <DatasetDetail projectId="p-1" datasetId="ds-A" />,
    )
    // Variables panel is mounted by default.
    expect(getByTestId('dataset-detail-panel-variables')).toBeDefined()
  })

  it('switches to the Transformations tab when clicked', () => {
    const { getByTestId, queryByTestId } = wrap(
      <DatasetDetail projectId="p-1" datasetId="ds-A" />,
    )
    fireEvent.click(getByTestId('tab-transformations'))
    expect(getByTestId('dataset-detail-panel-transformations')).toBeDefined()
    // Variables panel is no longer mounted.
    expect(queryByTestId('dataset-detail-panel-variables')).toBeNull()
  })

  it('switches to the Syntax tab when clicked', () => {
    const { getByTestId } = wrap(
      <DatasetDetail projectId="p-1" datasetId="ds-A" />,
    )
    fireEvent.click(getByTestId('tab-syntax'))
    expect(getByTestId('dataset-detail-panel-syntax')).toBeDefined()
  })
})
