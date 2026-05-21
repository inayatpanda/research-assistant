/**
 * Phase M2.3 — MobileLibrary smoke tests.
 *
 *   1. List of articles renders with the project name above it.
 *   2. The "+" FAB opens an action sheet with the three add modes.
 *   3. Typing in the search box filters the visible rows.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
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
  articles: [
    {
      id: 'a-1',
      user_id: 'u-1',
      project_id: 'p-1',
      title: 'Hip replacement outcomes at five years',
      authors: ['Smith J', 'Jones A'],
      journal: 'BMJ',
      year: 2024,
      volume: null,
      issue: null,
      pages: null,
      doi: '10.1136/bmj.k123',
      pmid: null,
      file_ref: null,
      file_type: null,
      abstract: 'Hips. Outcomes. Five years.',
      study_design: null,
      review_status: 'pending' as const,
      exclusion_reason: null,
      conflict_of_interest: null,
      source: 'doi' as const,
      reference_type: 'journal_article' as const,
      url: null,
      created_at: '2026-01-02T00:00:00Z',
      file_url: null,
    },
    {
      id: 'a-2',
      user_id: 'u-1',
      project_id: 'p-1',
      title: 'Knee revision arthroplasty registry analysis',
      authors: ['Brown C'],
      journal: 'JBJS',
      year: 2023,
      volume: null,
      issue: null,
      pages: null,
      doi: null,
      pmid: '37123456',
      file_ref: null,
      file_type: null,
      abstract: 'Knees. Registry. 10000 patients.',
      study_design: null,
      review_status: 'pending' as const,
      exclusion_reason: null,
      conflict_of_interest: null,
      source: 'pubmed' as const,
      reference_type: 'journal_article' as const,
      url: null,
      created_at: '2026-01-03T00:00:00Z',
      file_url: null,
    },
  ],
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  return {
    ...actual,
    projectsApi: { list: vi.fn(async () => hoisted.projects) },
    articlesApi: {
      list: vi.fn(async () => hoisted.articles),
      upload: vi.fn(),
      get: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
    ingestApi: {
      lookupDoi: vi.fn(),
      searchPubMed: vi.fn(),
      importFromMetadata: vi.fn(),
      importRis: vi.fn(),
      importBibtex: vi.fn(),
      duplicates: vi.fn(),
    },
  }
})

// Bypass the IDB cache layer.
vi.mock('@/mobile/lib/offlineLearn', async () => ({
  cacheable: async (_key: string, fetcher: () => Promise<unknown>) => ({
    data: await fetcher(),
    offline: false,
  }),
  entryKey: (c: string, s: string) => `${c}:${s}`,
  listKey: (c: string) => `__list:${c}`,
}))

import MobileLibrary from '@/mobile/pages/MobileLibrary'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/m/library" element={<MobileLibrary />} />
          <Route path="/m/reader/:articleId" element={<div>Reader</div>} />
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

describe('MobileLibrary', () => {
  it('renders the article list under the active project name', async () => {
    renderAt('/m/library')
    await waitFor(() => {
      expect(screen.getByTestId('mlib-row-a-1')).toBeTruthy()
      expect(screen.getByTestId('mlib-row-a-2')).toBeTruthy()
    })
    expect(
      screen.getByTestId('mlib-project-trigger').textContent,
    ).toContain('Outcome study')
  })

  it('opens the add-action sheet when the FAB is tapped', async () => {
    renderAt('/m/library')
    // Wait for the article list to appear — that confirms the project
    // load has settled so the FAB is enabled.
    await waitFor(() => screen.getByTestId('mlib-row-a-1'))
    const fab = screen.getByTestId('mlib-fab') as HTMLButtonElement
    expect(fab.disabled).toBe(false)
    fireEvent.click(fab)
    await waitFor(() => {
      expect(screen.getByTestId('mlib-action-upload')).toBeTruthy()
      expect(screen.getByTestId('mlib-action-doi')).toBeTruthy()
      expect(screen.getByTestId('mlib-action-pubmed')).toBeTruthy()
    })
  })

  it('search filters the list down to matching rows', async () => {
    renderAt('/m/library')
    await waitFor(() => screen.getByTestId('mlib-row-a-1'))
    const input = screen.getByTestId('mlib-search') as HTMLInputElement
    fireEvent.change(input, { target: { value: 'knee' } })
    await waitFor(() => {
      expect(screen.queryByTestId('mlib-row-a-1')).toBeNull()
      expect(screen.getByTestId('mlib-row-a-2')).toBeTruthy()
    })
  })
})
