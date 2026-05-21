/**
 * Phase M3.2 — MobileManuscriptReader citation-chip navigation.
 *
 * Tapping a <sup data-citation data-article-id="..."> token inside a
 * paragraph navigates to the mobile article reader rather than
 * opening the paragraph edit sheet.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  return {
    ...actual,
    projectsApi: {
      list: vi.fn(),
      get: vi.fn(async () => ({
        id: 'p-1',
        user_id: 'u-1',
        title: 'Project',
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
      })),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
    manuscriptApi: {
      getSection: vi.fn(async (_pid: string, name: string) => ({
        id: 'sec',
        user_id: 'u-1',
        project_id: 'p-1',
        section_name: name,
        content:
          name === 'Introduction'
            ? '<p>Smith reports a positive effect <sup data-citation data-article-id="a-42">[1]</sup>.</p>'
            : '',
        word_count: 5,
        updated_at: '2026-05-20T00:00:00Z',
      })),
      upsertSection: vi.fn(),
      buildArticlesTable: vi.fn(),
    },
    writingApi: { assist: vi.fn() },
    frontmatterApi: {
      authors: { list: vi.fn() },
      affiliations: { list: vi.fn() },
      frontmatter: { get: vi.fn() },
    },
    snapshotsApi: { list: vi.fn() },
    exportApi: {
      downloadDocx: vi.fn(),
      downloadPdf: vi.fn(),
      downloadBundle: vi.fn(),
    },
  }
})

vi.mock('@/mobile/lib/offlineLearn', async () => ({
  cacheable: async (_key: string, fetcher: () => Promise<unknown>) => ({
    data: await fetcher(),
    offline: false,
  }),
  entryKey: (c: string, s: string) => `${c}:${s}`,
  listKey: (c: string) => `__list:${c}`,
}))

import MobileManuscriptReader from '@/mobile/pages/MobileManuscriptReader'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            path="/m/manuscripts/:projectId"
            element={<MobileManuscriptReader />}
          />
          <Route
            path="/m/reader/:articleId"
            element={<div data-testid="article-reader" />}
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

describe('MobileManuscriptReader (citation chips)', () => {
  it('tapping a citation chip navigates to the mobile article reader', async () => {
    renderAt('/m/manuscripts/p-1')
    await waitFor(() => screen.getByTestId('mmr-para-Introduction-0'))
    const para = screen.getByTestId('mmr-para-Introduction-0')
    const chip = para.querySelector(
      'sup[data-citation][data-article-id="a-42"]',
    ) as HTMLElement | null
    expect(chip).not.toBeNull()
    fireEvent.click(chip as HTMLElement)
    await waitFor(() => {
      expect(screen.getByTestId('article-reader')).toBeTruthy()
    })
    // The edit sheet must not have opened — that's the bug guard for
    // chip-vs-paragraph click delegation.
    expect(screen.queryByTestId('mmr-edit-sheet')).toBeNull()
  })
})
