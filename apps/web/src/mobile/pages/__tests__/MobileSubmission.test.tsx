/**
 * Phase M5.3 — MobileSubmission smoke tests.
 *
 *   1. Cover letter card renders the persisted body_html under the
 *      active project.
 *   2. Tapping the cover-letter pencil opens the edit sheet; tapping
 *      "AI draft" calls ``coverLetterApi.draft``.
 *   3. The pre-submission check renders one row per check with the
 *      correct ok/warn state.
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
  cover: {
    id: 'cl-1',
    project_id: 'p-1',
    target_journal: 'lancet',
    novelty_points: ['Important finding'],
    body_html: '<p>Dear Editor,</p><p>Please consider our paper.</p>',
    ai_model: null,
    created_at: '2026-05-01T00:00:00Z',
    updated_at: '2026-05-01T00:00:00Z',
  },
  frontmatter: {
    id: 'fm-1',
    project_id: 'p-1',
    funding_statement: 'NIH grant',
    funders: [],
    ethics_irb: null,
    ethics_approval_number: null,
    ethics_consent: null,
    conflicts_statement: null,
    structured_abstract_enabled: false,
    structured_abstract: {
      background: null,
      methods: null,
      results: null,
      conclusions: null,
    },
    updated_at: '2026-05-01T00:00:00Z',
  },
  sections: [
    { id: 's-1', user_id: 'u-1', project_id: 'p-1', section_name: 'Abstract', content: 'A', word_count: 1, updated_at: '2026-05-01T00:00:00Z' },
    { id: 's-2', user_id: 'u-1', project_id: 'p-1', section_name: 'Introduction', content: 'I', word_count: 1, updated_at: '2026-05-01T00:00:00Z' },
    null,
    null,
    null,
    null,
  ],
  draft: vi.fn(),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  hoisted.draft.mockResolvedValue({
    ...hoisted.cover,
    body_html: '<p>AI-drafted letter</p>',
    ai_model: 'gemini',
  })
  return {
    ...actual,
    projectsApi: { list: vi.fn(async () => hoisted.projects) },
    coverLetterApi: {
      get: vi.fn(async () => hoisted.cover),
      update: vi.fn(async (_pid, body) => ({ ...hoisted.cover, ...body })),
      draft: hoisted.draft,
    },
    reviewerResponseApi: {
      list: vi.fn(async () => []),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
    frontmatterApi: {
      frontmatter: {
        get: vi.fn(async () => hoisted.frontmatter),
        patch: vi.fn(),
      },
    },
    manuscriptApi: {
      getSection: vi.fn(async (_pid: string, name: string) => {
        const i = ['Abstract', 'Introduction', 'Methodology', 'Results', 'Discussion', 'Conclusion'].indexOf(name)
        const sec = hoisted.sections[i]
        if (!sec) throw new Error('missing')
        return sec
      }),
    },
    figuresApi: {
      list: vi.fn(async () => []),
    },
    articlesApi: {
      list: vi.fn(async () => []),
    },
    bibliographyApi: {
      get: vi.fn(async () => ({ style: 'vancouver', entries: [] })),
    },
    exportApi: {
      downloadSubmissionPackage: vi.fn(async () => 'submission.zip'),
    },
  }
})

import MobileSubmission from '@/mobile/pages/MobileSubmission'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/m/submission" element={<MobileSubmission />} />
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

describe('MobileSubmission', () => {
  it('renders the cover letter preview from the backend', async () => {
    renderAt('/m/submission')
    await waitFor(() => {
      const card = screen.getByTestId('msubmission-cover-card')
      expect(card.textContent).toContain('Dear Editor')
    })
  })

  it('opens the edit sheet and triggers AI draft', async () => {
    renderAt('/m/submission')
    await waitFor(() => screen.getByTestId('msubmission-cover-card'))
    fireEvent.click(screen.getByTestId('msubmission-cover-edit'))
    await waitFor(() =>
      expect(screen.getByTestId('msubmission-cover-textarea')).toBeTruthy(),
    )
    fireEvent.click(screen.getByTestId('msubmission-cover-ai'))
    await waitFor(() => expect(hoisted.draft).toHaveBeenCalled())
  })

  it('renders the pre-submission check with correct ok/warn rows', async () => {
    renderAt('/m/submission')
    await waitFor(() => screen.getByTestId('msubmission-precheck-list'))
    await waitFor(() => {
      const frontmatter = screen.getByTestId('msubmission-precheck-frontmatter')
      expect(frontmatter.getAttribute('data-status')).toBe('ok')
      const figures = screen.getByTestId('msubmission-precheck-figures')
      expect(figures.getAttribute('data-status')).toBe('warn')
      const sections = screen.getByTestId('msubmission-precheck-sections')
      expect(sections.getAttribute('data-status')).toBe('warn')
      const cover = screen.getByTestId('msubmission-precheck-cover-letter')
      expect(cover.getAttribute('data-status')).toBe('ok')
    })
  })
})
