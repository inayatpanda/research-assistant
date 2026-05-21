/**
 * Phase 4.6 — Vitest smoke tests for the PeerReviewPage.
 *
 * Mounts the page with a mocked peerReviewsApi surface and asserts:
 *   1. Mode toggle switches between "My manuscript" and "Upload paper".
 *   2. History list renders past reviews with the recommendation badge.
 *   3. Clicking "Generate review" calls the manuscript-mode API.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProjectContext } from '@/lib/projectContext'

const hoisted = vi.hoisted(() => {
  const history = [
    {
      id: 'pr-1',
      project_id: 'p-1',
      source_type: 'manuscript' as const,
      source_title: 'Trial of widgets v1',
      recommendation: 'major_revision' as const,
      ai_model: 'gemini-2.5-flash',
      status: 'completed' as const,
      created_at: '2026-05-20T10:00:00Z',
      updated_at: '2026-05-20T10:00:00Z',
    },
    {
      id: 'pr-2',
      project_id: 'p-1',
      source_type: 'uploaded_pdf' as const,
      source_title: 'OtherPaper.pdf',
      recommendation: 'accept' as const,
      ai_model: 'gemini-2.5-flash',
      status: 'completed' as const,
      created_at: '2026-05-19T10:00:00Z',
      updated_at: '2026-05-19T10:00:00Z',
    },
  ]
  const newReview = {
    id: 'pr-new',
    project_id: 'p-1',
    source_type: 'manuscript' as const,
    source_title: 'Trial of widgets',
    source_file_ref: null,
    manuscript_snapshot: null,
    critique: {
      overall_impression: 'Generally well-written.',
      strengths: ['Clear question'],
      major_issues: ['Methods need detail'],
      minor_issues: [],
      methodological_concerns: [],
      statistical_concerns: [],
      reporting_concerns: [],
      presentation_concerns: [],
      references_concerns: [],
      suggestions_for_improvement: ['Add CONSORT flow diagram'],
      recommendation: 'major_revision',
    },
    recommendation: 'major_revision' as const,
    ai_model: 'gemini-2.5-flash',
    status: 'completed' as const,
    error: null,
    created_at: '2026-05-21T10:00:00Z',
    updated_at: '2026-05-21T10:00:00Z',
  }
  const mockGenerateFromManuscript = vi.fn(async () => newReview)
  return { history, newReview, mockGenerateFromManuscript }
})
const { mockGenerateFromManuscript } = hoisted

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  return {
    ...actual,
    peerReviewsApi: {
      list: vi.fn(async () => hoisted.history),
      get: vi.fn(async () => ({ ...hoisted.history[0], source_file_ref: null, manuscript_snapshot: null, critique: {}, error: null })),
      generateFromManuscript: hoisted.mockGenerateFromManuscript,
      generateFromUpload: vi.fn(),
      delete: vi.fn(),
      download: vi.fn(),
    },
  }
})

import PeerReviewPage from '../PeerReviewPage'

function wrap() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/projects/p-1/peer-review']}>
        <ProjectContext.Provider value={{ projectId: 'p-1', project: null }}>
          <Routes>
            <Route
              path="/projects/:projectId/peer-review"
              element={<PeerReviewPage />}
            />
          </Routes>
        </ProjectContext.Provider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  mockGenerateFromManuscript.mockClear()
})

describe('PeerReviewPage', () => {
  it('toggles between manuscript and upload modes', async () => {
    wrap()
    // Default mode is manuscript, so generate button is visible.
    expect(screen.getByTestId('peer-review-page-shell')).toBeDefined()
    expect(screen.getByTestId('peer-review-generate-button')).toBeDefined()

    // Click "Upload paper" — dropzone appears, generate button goes away.
    fireEvent.click(screen.getByTestId('peer-review-mode-upload'))
    expect(screen.getByTestId('peer-review-dropzone')).toBeDefined()
    expect(screen.queryByTestId('peer-review-generate-button')).toBeNull()

    // Toggle back.
    fireEvent.click(screen.getByTestId('peer-review-mode-manuscript'))
    expect(screen.getByTestId('peer-review-generate-button')).toBeDefined()
  })

  it('renders the history list with recommendation badges', async () => {
    wrap()
    await waitFor(() => {
      expect(screen.getByTestId('peer-review-history-item-pr-1')).toBeDefined()
      expect(screen.getByTestId('peer-review-history-item-pr-2')).toBeDefined()
    })
    // Badge colours/labels per row.
    expect(
      screen.getByTestId('peer-review-history-item-pr-1').textContent,
    ).toContain('Major Revision')
    expect(
      screen.getByTestId('peer-review-history-item-pr-2').textContent,
    ).toContain('Accept')
  })

  it('invokes the manuscript-mode generator on Generate review click', async () => {
    wrap()
    const btn = screen.getByTestId('peer-review-generate-button')
    fireEvent.click(btn)
    await waitFor(() => {
      expect(mockGenerateFromManuscript).toHaveBeenCalledTimes(1)
    })
  })
})
