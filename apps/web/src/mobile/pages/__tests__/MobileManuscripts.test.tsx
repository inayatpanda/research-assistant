/**
 * Phase M3.1 — MobileManuscripts smoke tests.
 *
 *   1. List of projects renders, each card showing title + study type.
 *   2. The "+" FAB opens the create sheet.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

const hoisted = vi.hoisted(() => ({
  projects: [
    {
      id: 'p-1',
      user_id: 'u-1',
      title: 'Hip arthroplasty outcomes',
      study_type: 'Outcome Study',
      citation_style: 'vancouver' as const,
      ai_provider: 'gemini' as const,
      target_journal: null,
      prospero_number: null,
      clinicaltrials_number: null,
      template_journal: null,
      inline_citation_mode: 'bracket_numeric' as const,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: new Date(Date.now() - 60_000).toISOString(),
    },
    {
      id: 'p-2',
      user_id: 'u-1',
      title: 'Knee revision case series',
      study_type: 'Retrospective Case Series',
      citation_style: 'vancouver' as const,
      ai_provider: 'gemini' as const,
      target_journal: null,
      prospero_number: null,
      clinicaltrials_number: null,
      template_journal: null,
      inline_citation_mode: 'bracket_numeric' as const,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-04-01T00:00:00Z',
    },
  ],
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  return {
    ...actual,
    projectsApi: {
      list: vi.fn(async () => hoisted.projects),
      get: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
    frontmatterApi: {
      authors: { list: vi.fn() },
      affiliations: { list: vi.fn() },
      frontmatter: {
        get: vi.fn(async () => ({
          id: 'fm-1',
          project_id: 'p-1',
          funding_statement: null,
          funders: [],
          ethics_irb: null,
          ethics_approval_number: null,
          ethics_consent: null,
          conflicts_statement: null,
          structured_abstract_enabled: false,
          structured_abstract: {
            background: 'Hip arthroplasty is common.',
            methods: '',
            results: '',
            conclusions: '',
          },
          updated_at: '2026-01-01T00:00:00Z',
        })),
      },
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

import MobileManuscripts from '@/mobile/pages/MobileManuscripts'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/m/manuscripts" element={<MobileManuscripts />} />
          <Route
            path="/m/manuscripts/:projectId"
            element={<div data-testid="reader-placeholder">Reader</div>}
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

describe('MobileManuscripts', () => {
  it('renders the list of projects with study-type badges', async () => {
    renderAt('/m/manuscripts')
    await waitFor(() => {
      expect(screen.getByTestId('mmanu-row-p-1')).toBeTruthy()
      expect(screen.getByTestId('mmanu-row-p-2')).toBeTruthy()
    })
    expect(screen.getByTestId('mmanu-row-p-1').textContent).toContain(
      'Hip arthroplasty outcomes',
    )
    expect(screen.getByTestId('mmanu-row-p-1').textContent).toContain(
      'Outcome Study',
    )
  })

  it('opens the create sheet when the FAB is tapped', async () => {
    renderAt('/m/manuscripts')
    await waitFor(() => screen.getByTestId('mmanu-row-p-1'))
    const fab = screen.getByTestId('mmanu-fab') as HTMLButtonElement
    fireEvent.click(fab)
    await waitFor(() => {
      expect(screen.getByTestId('mmanu-create-sheet')).toBeTruthy()
      expect(screen.getByTestId('mmanu-title-input')).toBeTruthy()
    })
  })
})
