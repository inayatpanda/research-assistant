/**
 * Phase M4.5 — MobileStatsResults smoke tests.
 *
 *   1. Headline + interpretation cards render from a completed analysis.
 *   2. Tapping "Push" opens the section picker and dispatches the push
 *      mutation when a section is chosen.
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
  push: vi.fn(async () => ({
    id: 's-1',
    user_id: 'u-1',
    project_id: 'p-1',
    section_name: 'Results' as const,
    content: '<p>Pushed</p>',
    word_count: 1,
    updated_at: '2026-05-21T00:00:00Z',
  })),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  return {
    ...actual,
    projectsApi: {
      list: vi.fn(async () => [
        {
          id: 'p-1',
          user_id: 'u-1',
          title: 'Outcome study',
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
        },
      ]),
    },
    analysesApi: {
      get: vi.fn(async () => ({
        id: 'a-1',
        project_id: 'p-1',
        dataset_id: 'ds-1',
        question_type: 'group_comparison',
        chosen_test: 'independent_t',
        recommendation_rationale: '',
        variables: { outcome: 'age', groups: 'sex' },
        status: 'completed',
        created_at: '2026-05-21T00:00:00Z',
        result: {
          summary: { p_value: 0.011, cohens_d: 0.45, ci_lower: 0.2, ci_upper: 0.7 },
          assumptions: { shapiro_p: 0.32 },
          chart: null,
          ai_interpretation:
            'There is a significant difference between groups (p = 0.011).',
        },
      })),
      pushToManuscript: hoisted.push,
      create: vi.fn(),
      run: vi.fn(),
      interpret: vi.fn(),
      delete: vi.fn(),
      listForDataset: vi.fn(),
      recommend: vi.fn(),
      updateChartLabels: vi.fn(),
    },
  }
})

import MobileStatsResults from '@/mobile/pages/MobileStatsResults'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route
            path="/m/stats/:datasetId/results/:analysisId"
            element={<MobileStatsResults />}
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

describe('MobileStatsResults', () => {
  it('renders the headline card + interpretation card', async () => {
    renderAt('/m/stats/ds-1/results/a-1')
    await waitFor(() => {
      expect(screen.getByTestId('mstats-headline-card')).toBeTruthy()
      expect(screen.getByTestId('mstats-interpret-card')).toBeTruthy()
    })
    expect(screen.getByTestId('mstats-headline-p').textContent).toContain('0.011')
  })

  it('opens the push sheet and pushes to a chosen section', async () => {
    renderAt('/m/stats/ds-1/results/a-1')
    // Wait for the headline card so the analysis query has settled
    // and aiText is present (enables the push button).
    await waitFor(() => screen.getByTestId('mstats-headline-card'))
    const pushBtn = screen.getByTestId('mstats-results-push') as HTMLButtonElement
    expect(pushBtn.disabled).toBe(false)
    fireEvent.click(pushBtn)
    await waitFor(() =>
      expect(screen.getByTestId('mstats-push-results')).toBeTruthy(),
    )
    fireEvent.click(screen.getByTestId('mstats-push-results'))
    await waitFor(() => expect(hoisted.push).toHaveBeenCalled())
  })
})
