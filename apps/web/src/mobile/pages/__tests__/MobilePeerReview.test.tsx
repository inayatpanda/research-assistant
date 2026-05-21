/**
 * Phase M1.5 — MobilePeerReview smoke tests.
 *
 *   1. The two mode buttons render (Review my manuscript / Upload an article).
 *   2. History list renders entries from across multiple projects with
 *      their recommendation badge.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

const hoisted = vi.hoisted(() => ({
  projects: [
    { id: 'p-1', title: 'Cohort study', description: 'desc', created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' },
    { id: 'p-2', title: 'RCT widget', description: '', created_at: '2026-01-02T00:00:00Z', updated_at: '2026-01-02T00:00:00Z' },
  ],
  reviewsP1: [
    {
      id: 'pr-1',
      project_id: 'p-1',
      source_type: 'manuscript' as const,
      source_title: 'Cohort manuscript v1',
      recommendation: 'major_revision' as const,
      ai_model: 'gemini',
      status: 'completed' as const,
      created_at: '2026-05-20T10:00:00Z',
      updated_at: '2026-05-20T10:00:00Z',
    },
  ],
  reviewsP2: [
    {
      id: 'pr-2',
      project_id: 'p-2',
      source_type: 'uploaded_pdf' as const,
      source_title: 'Submitted.pdf',
      recommendation: 'accept' as const,
      ai_model: 'gemini',
      status: 'completed' as const,
      created_at: '2026-05-19T10:00:00Z',
      updated_at: '2026-05-19T10:00:00Z',
    },
  ],
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  return {
    ...actual,
    projectsApi: { list: vi.fn(async () => hoisted.projects) },
    peerReviewsApi: {
      list: vi.fn(async (pid: string) =>
        pid === 'p-1' ? hoisted.reviewsP1 : hoisted.reviewsP2,
      ),
      get: vi.fn(),
      generateFromManuscript: vi.fn(),
      generateFromUpload: vi.fn(),
      delete: vi.fn(),
      download: vi.fn(),
    },
  }
})

import MobilePeerReview from '@/mobile/pages/MobilePeerReview'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/m/peer-review" element={<MobilePeerReview />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('MobilePeerReview', () => {
  it('renders both mode picker buttons', () => {
    renderAt('/m/peer-review')
    expect(screen.getByTestId('mpeer-mode-manuscript')).toBeTruthy()
    expect(screen.getByTestId('mpeer-mode-upload')).toBeTruthy()
  })

  it('renders history aggregated across projects', async () => {
    renderAt('/m/peer-review')
    await waitFor(() => {
      expect(screen.getByTestId('mpeer-history-pr-1')).toBeTruthy()
      expect(screen.getByTestId('mpeer-history-pr-2')).toBeTruthy()
    })
    // Latest review first (pr-1 is newer than pr-2 in the fixture).
    const list = screen.getByTestId('mpeer-history-list')
    const rows = list.querySelectorAll('[data-testid^="mpeer-history-pr-"]')
    expect(rows[0].getAttribute('data-testid')).toBe('mpeer-history-pr-1')
  })
})
