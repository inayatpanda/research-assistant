/**
 * Phase D4 — MobileManuscriptReader highlights flow.
 *
 *   1. Toggling Highlights mode via the overflow menu flips the
 *      body's data-highlights-mode attribute (off → on → off).
 *   2. Existing comments render as marked spans with data-comment-id
 *      attributes wired to the correct comment.
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
  createComment: vi.fn(
    async (_pid: string, body: { section_name: string; anchor_start: number; anchor_end: number; body: string }) => ({
      id: 'c-new',
      project_id: 'p-1',
      section_name: body.section_name,
      anchor_start: body.anchor_start,
      anchor_end: body.anchor_end,
      body: body.body,
      resolved: false,
      created_at: '2026-05-21T00:00:00Z',
      updated_at: '2026-05-21T00:00:00Z',
    }),
  ),
  listComments: vi.fn(async () => [
    {
      id: 'c-existing',
      project_id: 'p-1',
      section_name: 'Introduction',
      // "Hello world." → "world" starts at offset 6, ends at 11.
      anchor_start: 6,
      anchor_end: 11,
      body: '[colour:method]a note',
      resolved: false,
      created_at: '2026-05-20T00:00:00Z',
      updated_at: '2026-05-20T00:00:00Z',
    },
  ]),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  const SECTION_CONTENT: Record<string, string> = {
    Abstract: '',
    Introduction: '<p>Hello world.</p>',
    Methodology: '',
    Results: '',
    Discussion: '',
    Conclusion: '',
  }
  return {
    ...actual,
    projectsApi: {
      get: vi.fn(async () => ({
        id: 'p-1',
        user_id: 'u-1',
        title: 'Highlight test project',
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
      list: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
    manuscriptApi: {
      getSection: vi.fn(async (_pid: string, name: string) => ({
        id: `sec-${name}`,
        user_id: 'u-1',
        project_id: 'p-1',
        section_name: name,
        content: SECTION_CONTENT[name] ?? '',
        word_count: 2,
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
    commentsApi: {
      list: hoisted.listComments,
      create: hoisted.createComment,
      update: vi.fn(),
      delete: vi.fn(),
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

describe('MobileManuscriptReader — Highlights mode (D4)', () => {
  it('toggles highlights mode from the overflow menu', async () => {
    renderAt('/m/manuscripts/p-1')
    await waitFor(() => screen.getByTestId('mmr-body'))
    const body = screen.getByTestId('mmr-body')
    expect(body.getAttribute('data-highlights-mode')).toBe('0')

    fireEvent.click(screen.getByTestId('mmr-overflow'))
    await waitFor(() => screen.getByTestId('mmr-overflow-highlights'))
    fireEvent.click(screen.getByTestId('mmr-overflow-highlights'))

    await waitFor(() => {
      expect(
        screen.getByTestId('mmr-body').getAttribute('data-highlights-mode'),
      ).toBe('1')
    })

    // Flip back off via the menu.
    fireEvent.click(screen.getByTestId('mmr-overflow'))
    await waitFor(() => screen.getByTestId('mmr-overflow-highlights'))
    fireEvent.click(screen.getByTestId('mmr-overflow-highlights'))
    await waitFor(() => {
      expect(
        screen.getByTestId('mmr-body').getAttribute('data-highlights-mode'),
      ).toBe('0')
    })
  })

  it('renders an existing comment as a marked span tied to its comment id', async () => {
    renderAt('/m/manuscripts/p-1')
    await waitFor(() => screen.getByTestId('mmr-para-Introduction-0'))
    // The existing comment covers the word "world" — find a span with
    // data-comment-id pointing at our seed comment.
    const para = screen.getByTestId('mmr-para-Introduction-0')
    const marked = para.querySelectorAll('[data-comment-id="c-existing"]')
    expect(marked.length).toBeGreaterThan(0)
    // The marked content should contain "world".
    const text = Array.from(marked)
      .map((el) => el.textContent ?? '')
      .join('')
    expect(text).toContain('world')

    // Tapping the marked span opens the comment edit sheet.
    fireEvent.click(marked[0])
    await waitFor(() => screen.getByTestId('mmr-comment-sheet'))
    expect(screen.getByTestId('mmr-comment-quote').textContent).toContain(
      'world',
    )
  })
})
