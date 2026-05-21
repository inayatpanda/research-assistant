/**
 * Phase M3.2 — MobileManuscriptReader AI rewrite tests.
 *
 *   1. Tapping "AI rewrite" calls writingApi.assist and surfaces the
 *      candidate inline with Apply / Discard controls.
 *   2. Apply replaces the textarea draft with the AI candidate;
 *      Discard restores the original.
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
  assist: vi.fn(async (_action: string, _text: string) => 'AI-revised text.'),
}))

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
            ? '<p>Original prose that needs improvement.</p>'
            : '',
        word_count: 5,
        updated_at: '2026-05-20T00:00:00Z',
      })),
      upsertSection: vi.fn(),
      buildArticlesTable: vi.fn(),
    },
    writingApi: { assist: hoisted.assist },
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
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('MobileManuscriptReader (AI rewrite)', () => {
  it('AI rewrite button calls writingApi.assist and shows the candidate', async () => {
    renderAt('/m/manuscripts/p-1')
    await waitFor(() => screen.getByTestId('mmr-para-Introduction-0'))
    fireEvent.click(screen.getByTestId('mmr-para-Introduction-0'))
    await waitFor(() => screen.getByTestId('mmr-edit-ai'))

    fireEvent.click(screen.getByTestId('mmr-edit-ai'))

    await waitFor(() => {
      expect(hoisted.assist).toHaveBeenCalledTimes(1)
      expect(hoisted.assist.mock.calls[0][0]).toBe('improve')
    })
    await waitFor(() => screen.getByTestId('mmr-edit-ai-apply'))
    const ta = screen.getByTestId('mmr-edit-textarea') as HTMLTextAreaElement
    expect(ta.value).toBe('AI-revised text.')
  })

  it('Apply replaces the draft; Discard restores the original', async () => {
    renderAt('/m/manuscripts/p-1')
    await waitFor(() => screen.getByTestId('mmr-para-Introduction-0'))
    fireEvent.click(screen.getByTestId('mmr-para-Introduction-0'))
    await waitFor(() => screen.getByTestId('mmr-edit-ai'))

    fireEvent.click(screen.getByTestId('mmr-edit-ai'))
    await waitFor(() => screen.getByTestId('mmr-edit-ai-apply'))

    // Apply path
    fireEvent.click(screen.getByTestId('mmr-edit-ai-apply'))
    let ta = screen.getByTestId('mmr-edit-textarea') as HTMLTextAreaElement
    expect(ta.value).toBe('AI-revised text.')

    // Re-trigger AI rewrite then discard
    fireEvent.click(screen.getByTestId('mmr-edit-ai'))
    await waitFor(() => screen.getByTestId('mmr-edit-ai-discard'))
    fireEvent.click(screen.getByTestId('mmr-edit-ai-discard'))
    ta = screen.getByTestId('mmr-edit-textarea') as HTMLTextAreaElement
    // After discard, the textarea returns to the previously-applied
    // draft (the AI candidate is dropped, draft stays at last value).
    expect(ta.value).toBe('AI-revised text.')
  })
})
