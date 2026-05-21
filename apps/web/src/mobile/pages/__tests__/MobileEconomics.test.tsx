/**
 * Phase M5.1 — MobileEconomics smoke tests.
 *
 *   1. All three calculator cards render under the active project.
 *   2. Filling the ICER form + tapping submit yields a result block with
 *      the verdict and CI bracket.
 *   3. Tapping the QALY info button opens a sheet that fetches the Learn
 *      entry via ``learnApi.getEconomics``.
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
  analyses: [] as Array<unknown>,
  getEconomics: vi.fn(async () => ({
    slug: 'quality-adjusted-life-year',
    title: 'Quality-adjusted life years',
    short_blurb: '',
    body_md: '# QALY\n\nA quality-adjusted life year is...',
    related_concepts: [],
    concept_family: 'outcomes',
  })),
}))

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<Record<string, unknown>>('@/lib/api')
  return {
    ...actual,
    projectsApi: { list: vi.fn(async () => hoisted.projects) },
    economicAnalysesApi: {
      list: vi.fn(async () => hoisted.analyses),
    },
    learnApi: {
      getEconomics: hoisted.getEconomics,
    },
  }
})

// Stub MarkdownView to avoid pulling the full Markdown pipeline.
vi.mock('@/components/learn/MarkdownView', () => ({
  MarkdownView: ({ source }: { source: string }) => (
    <div data-testid="md-stub">{source}</div>
  ),
}))

import MobileEconomics from '@/mobile/pages/MobileEconomics'

function renderAt(path: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/m/economics" element={<MobileEconomics />} />
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

describe('MobileEconomics', () => {
  it('renders the three calculator cards under the active project', async () => {
    renderAt('/m/economics')
    await waitFor(() => {
      expect(screen.getByTestId('meconomics-icer')).toBeTruthy()
      expect(screen.getByTestId('meconomics-qaly')).toBeTruthy()
      expect(screen.getByTestId('meconomics-nmb')).toBeTruthy()
    })
    await waitFor(() =>
      expect(
        screen.getByTestId('meconomics-project-trigger').textContent,
      ).toContain('Outcome study'),
    )
  })

  it('submits the ICER form and shows a verdict + CI', async () => {
    renderAt('/m/economics')
    await waitFor(() => screen.getByTestId('meconomics-icer'))
    fireEvent.change(screen.getByTestId('meconomics-icer-cost-a'), {
      target: { value: '15000' },
    })
    fireEvent.change(screen.getByTestId('meconomics-icer-cost-b'), {
      target: { value: '10000' },
    })
    fireEvent.change(screen.getByTestId('meconomics-icer-qaly-a'), {
      target: { value: '2.5' },
    })
    fireEvent.change(screen.getByTestId('meconomics-icer-qaly-b'), {
      target: { value: '2.0' },
    })
    fireEvent.click(screen.getByTestId('meconomics-icer-submit'))
    const result = await waitFor(() =>
      screen.getByTestId('meconomics-icer-result'),
    )
    // (15000 - 10000) / (2.5 - 2.0) = 10 000 → below 30 000 WTP → cost-effective
    expect(result.textContent).toContain('cost-effective')
    expect(result.textContent).toContain('95% CI')
  })

  it('opens the QALY info sheet and loads the Learn entry', async () => {
    renderAt('/m/economics')
    await waitFor(() => screen.getByTestId('meconomics-qaly'))
    fireEvent.click(screen.getByTestId('meconomics-qaly-info'))
    await waitFor(() => {
      expect(hoisted.getEconomics).toHaveBeenCalledWith(
        'quality-adjusted-life-year',
      )
      expect(screen.getByTestId('meconomics-info-body')).toBeTruthy()
    })
  })
})
