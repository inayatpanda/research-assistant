/**
 * Phase M4.1 — MobileStatsUpload smoke tests.
 *
 *   1. The upload card + existing-dataset list both render under the
 *      active project name.
 *   2. Picking a file triggers ``datasetsApi.upload`` and navigates to
 *      the preview route on success.
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
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const hoisted = vi.hoisted(() => ({
  projects: [
    {
      id: 'p-1',
      user_id: 'u-1',
      title: 'Outcome study',
      study_type: 'Outcome Study',
      citation_style: 'vancouver' as const,
      ai_provider: 'gemini' as const,
      target_journal: null,
      prospero_number: null,
      clinicaltrials_number: null,
      template_journal: null,
      inline_citation_mode: 'bracket_numeric' as const,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
    },
  ],
  datasets: [
    {
      id: 'ds-1',
      project_id: 'p-1',
      filename: 'masterchart.csv',
      file_type: 'csv',
      n_rows: 120,
      n_columns: 8,
      created_at: '2026-05-01T00:00:00Z',
      variables: [],
      derived_from_dataset_id: null,
      derived_from_dataset_ids: null,
      dataset_metadata: null,
      header_sanitisation_report: [],
    },
  ],
  upload: vi.fn(async () => ({
    id: 'ds-2',
    project_id: 'p-1',
    filename: 'new.csv',
    file_type: 'csv',
    n_rows: 50,
    n_columns: 4,
    created_at: '2026-05-21T00:00:00Z',
    variables: [],
    derived_from_dataset_id: null,
    derived_from_dataset_ids: null,
    dataset_metadata: null,
    header_sanitisation_report: [],
  })),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  return {
    ...actual,
    projectsApi: { list: vi.fn(async () => hoisted.projects) },
    datasetsApi: {
      list: vi.fn(async () => hoisted.datasets),
      upload: hoisted.upload,
      get: vi.fn(),
      delete: vi.fn(),
      updateVariable: vi.fn(),
      updateVariableDisplayLabel: vi.fn(),
      preview: vi.fn(),
    },
  }
})

import MobileStatsUpload from '@/mobile/pages/MobileStatsUpload'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/m/stats" element={<MobileStatsUpload />} />
          <Route
            path="/m/stats/:datasetId/preview"
            element={<div data-testid="preview-route">preview</div>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  window.localStorage?.clear?.()
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('MobileStatsUpload', () => {
  it('renders the upload card + existing-dataset list', async () => {
    renderAt('/m/stats')
    await waitFor(() => {
      expect(screen.getByTestId('mstats-upload-card')).toBeTruthy()
      expect(screen.getByTestId('mstats-ds-row-ds-1')).toBeTruthy()
    })
    expect(
      screen.getByTestId('mstats-project-trigger').textContent,
    ).toContain('Outcome study')
  })

  it('uploads a chosen file and navigates to the preview route', async () => {
    renderAt('/m/stats')
    // Wait until the dataset list query settles — that guarantees the
    // projects query also resolved, so activeProjectId is set and the
    // hidden file input is no longer disabled.
    await waitFor(() => screen.getByTestId('mstats-ds-row-ds-1'))
    const input = screen.getByTestId('mstats-file-input') as HTMLInputElement
    expect(input.disabled).toBe(false)
    const file = new File(['a,b\n1,2'], 'data.csv', { type: 'text/csv' })
    fireEvent.change(input, { target: { files: [file] } })
    await waitFor(() => expect(hoisted.upload).toHaveBeenCalled())
    await waitFor(() =>
      expect(screen.getByTestId('preview-route')).toBeTruthy(),
    )
  })
})
