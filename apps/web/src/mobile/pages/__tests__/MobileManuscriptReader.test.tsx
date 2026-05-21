/**
 * Phase M3.2 — MobileManuscriptReader smoke tests.
 *
 *   1. All 6 IMRaD sections render with paragraphs split correctly.
 *   2. Tapping a paragraph opens the edit sheet pre-filled with text.
 *   3. Saving an edit calls manuscriptApi.upsertSection with the joined
 *      content + the edited paragraph in place.
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
  upsertSection: vi.fn(async (_pid: string, _section: string, content: string) => ({
    id: 's-1',
    user_id: 'u-1',
    project_id: 'p-1',
    section_name: 'Introduction',
    content,
    word_count: 5,
    updated_at: '2026-05-21T00:00:00Z',
  })),
  assist: vi.fn(),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  function section(name: string, content: string) {
    return {
      id: `sec-${name}`,
      user_id: 'u-1',
      project_id: 'p-1',
      section_name: name,
      content,
      word_count: content.split(/\s+/).length,
      updated_at: '2026-05-20T00:00:00Z',
    }
  }
  const SECTION_CONTENT: Record<string, string> = {
    Abstract: '<p>Hip arthroplasty is a common procedure.</p>',
    Introduction:
      '<p>The Bayesian model is used in arthroplasty research.</p><p>This paragraph two needs editing.</p>',
    Methodology:
      '<p>We compared cohorts using propensity-score matching.</p>',
    Results: '<p>Outcomes favoured the arthroplasty group.</p>',
    Discussion: '<p>The results indicate that arthroplasty is effective.</p>',
    Conclusion: '<p>Arthroplasty is the preferred treatment.</p>',
  }
  return {
    ...actual,
    projectsApi: {
      list: vi.fn(),
      get: vi.fn(async () => ({
        id: 'p-1',
        user_id: 'u-1',
        title: 'Hip arthroplasty outcomes',
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
      getSection: vi.fn(async (_pid: string, name: string) =>
        section(name, SECTION_CONTENT[name] ?? ''),
      ),
      upsertSection: hoisted.upsertSection,
      buildArticlesTable: vi.fn(),
    },
    writingApi: { assist: hoisted.assist },
    frontmatterApi: {
      authors: { list: vi.fn(async () => []) },
      affiliations: { list: vi.fn(async () => []) },
      frontmatter: { get: vi.fn() },
    },
    snapshotsApi: { list: vi.fn(async () => []) },
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

describe('MobileManuscriptReader', () => {
  it('renders all six IMRaD section headers and their paragraphs', async () => {
    renderAt('/m/manuscripts/p-1')
    await waitFor(() => {
      expect(screen.getByTestId('mmr-section-header-Abstract')).toBeTruthy()
      expect(screen.getByTestId('mmr-section-header-Introduction')).toBeTruthy()
      expect(screen.getByTestId('mmr-section-header-Methodology')).toBeTruthy()
      expect(screen.getByTestId('mmr-section-header-Results')).toBeTruthy()
      expect(screen.getByTestId('mmr-section-header-Discussion')).toBeTruthy()
      expect(screen.getByTestId('mmr-section-header-Conclusion')).toBeTruthy()
    })
    // Introduction was split into two paragraphs.
    expect(screen.getByTestId('mmr-para-Introduction-0').textContent).toContain(
      'Bayesian model',
    )
    expect(screen.getByTestId('mmr-para-Introduction-1').textContent).toContain(
      'paragraph two',
    )
  })

  it('opens the edit sheet when a paragraph is tapped', async () => {
    renderAt('/m/manuscripts/p-1')
    await waitFor(() => screen.getByTestId('mmr-para-Introduction-1'))
    fireEvent.click(screen.getByTestId('mmr-para-Introduction-1'))
    await waitFor(() => {
      expect(screen.getByTestId('mmr-edit-sheet')).toBeTruthy()
    })
    const ta = screen.getByTestId('mmr-edit-textarea') as HTMLTextAreaElement
    expect(ta.value).toContain('paragraph two')
    expect(screen.getByTestId('mmr-edit-section-badge').textContent).toContain(
      'Introduction',
    )
  })

  it('saves an edited paragraph by patching the section', async () => {
    renderAt('/m/manuscripts/p-1')
    await waitFor(() => screen.getByTestId('mmr-para-Introduction-1'))
    fireEvent.click(screen.getByTestId('mmr-para-Introduction-1'))
    await waitFor(() => screen.getByTestId('mmr-edit-textarea'))

    const ta = screen.getByTestId('mmr-edit-textarea') as HTMLTextAreaElement
    fireEvent.change(ta, { target: { value: 'Refined second paragraph.' } })

    fireEvent.click(screen.getByTestId('mmr-edit-save'))

    await waitFor(() => {
      expect(hoisted.upsertSection).toHaveBeenCalledTimes(1)
    })
    const args = hoisted.upsertSection.mock.calls[0]
    expect(args[0]).toBe('p-1')
    expect(args[1]).toBe('Introduction')
    // The joined HTML still contains the unedited first paragraph and
    // the new second paragraph text.
    expect(args[2]).toContain('Bayesian model')
    expect(args[2]).toContain('Refined second paragraph.')
    expect(args[2]).not.toContain('paragraph two needs editing')
  })
})
