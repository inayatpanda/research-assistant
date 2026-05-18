import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import type { Analysis, Dataset } from '@/lib/api'

import { AnalysisResultCard } from '../AnalysisResultCard'

const PNG_DATA_URI =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNgYGBgAAAABQABcuP+EgAAAABJRU5ErkJggg=='

const DATASET: Dataset = {
  id: 'ds-1',
  project_id: 'p-1',
  filename: 'data.csv',
  file_type: 'csv',
  n_rows: 12,
  n_columns: 2,
  created_at: '2026-05-18T00:00:00Z',
  variables: [],
}

function makeAnalysis(overrides: Partial<Analysis> = {}): Analysis {
  return {
    id: 'a-1',
    project_id: 'p-1',
    dataset_id: 'ds-1',
    question_type: 'group_comparison',
    chosen_test: 'independent_t',
    recommendation_rationale: 'Two-group continuous outcome.',
    variables: { outcome: 'score', groups: 'group' },
    status: 'completed',
    created_at: '2026-05-18T00:00:00Z',
    result: {
      summary: {
        statistic: 3.1,
        p_value: 0.01,
        effect_size: 1.2,
        ci_low: 0.5,
        ci_high: 1.9,
        n: 12,
        df: 10,
      },
      assumptions: {},
      chart: null,
      ai_interpretation: null,
    },
    ...overrides,
  }
}

function renderWithProviders(node: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={qc}>{node}</QueryClientProvider>
    </MemoryRouter>,
  )
}

afterEach(() => cleanup())

describe('AnalysisResultCard — chart slot', () => {
  it('renders the chart image when result has a PNG chart', () => {
    const analysis = makeAnalysis({
      result: {
        summary: {
          statistic: 3.1,
          p_value: 0.01,
          effect_size: 1.2,
          ci_low: 0.5,
          ci_high: 1.9,
          n: 12,
          df: 10,
        },
        assumptions: {},
        chart: {
          format: 'png',
          data_uri: PNG_DATA_URI,
          byte_size: 70,
        },
        ai_interpretation: null,
      },
    })
    const { container } = renderWithProviders(
      <AnalysisResultCard projectId="p-1" dataset={DATASET} analysis={analysis} />,
    )
    const img = container.querySelector('img[alt$="chart"]') as HTMLImageElement | null
    expect(img).not.toBeNull()
    expect(img!.src).toBe(PNG_DATA_URI)
  })

  it('renders no chart node when chart is null', () => {
    const analysis = makeAnalysis()
    const { container } = renderWithProviders(
      <AnalysisResultCard projectId="p-1" dataset={DATASET} analysis={analysis} />,
    )
    expect(container.querySelector('img[alt$="chart"]')).toBeNull()
  })

  it('renders no chart node when chart payload is malformed', () => {
    const analysis = makeAnalysis({
      result: {
        summary: {
          statistic: 3.1,
          p_value: 0.01,
          effect_size: 1.2,
          ci_low: 0.5,
          ci_high: 1.9,
          n: 12,
          df: 10,
        },
        assumptions: {},
        // Old-shape chart from Phase 6 (pre-8.5). The card must ignore it.
        chart: { type: 'kaplan_meier', series: [] },
        ai_interpretation: null,
      },
    })
    const { container } = renderWithProviders(
      <AnalysisResultCard projectId="p-1" dataset={DATASET} analysis={analysis} />,
    )
    expect(container.querySelector('img[alt$="chart"]')).toBeNull()
  })
})
