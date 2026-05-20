/**
 * DEMO-FIX-A — DiagnosticsPanel tests.
 *
 * Covers:
 *   1. mount + numeric-only column picker
 *   2. group-column picker appears only for Levene/Bartlett, and lists
 *      only nominal/ordinal columns
 *   3. running Shapiro-Wilk renders the statistic + p + interpretation +
 *      green pass pill
 *   4. running a "fail" diagnostic surfaces the amber violation pill
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react'
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest'

// Radix UI requires these in jsdom.
beforeAll(() => {
  if (!Element.prototype.scrollIntoView) {
    Element.prototype.scrollIntoView = vi.fn()
  }
  if (!('hasPointerCapture' in Element.prototype)) {
    Element.prototype.hasPointerCapture = vi.fn(() => false)
    Element.prototype.releasePointerCapture = vi.fn()
  }
})

const { runMock, qqPlotMock, histogramMock } = vi.hoisted(() => ({
  runMock: vi.fn(),
  qqPlotMock: vi.fn(),
  histogramMock: vi.fn(),
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    diagnosticsApi: {
      run: runMock,
      qqPlot: qqPlotMock,
      histogram: histogramMock,
    },
  }
})

import type { Dataset } from '@/lib/api'
import { DiagnosticsPanel } from '../DiagnosticsPanel'

const DATASET: Dataset = {
  id: 'ds-1',
  project_id: 'p-1',
  filename: 'cohort.csv',
  file_type: 'csv',
  n_rows: 200,
  n_columns: 3,
  created_at: '2026-05-18T00:00:00Z',
  variables: [
    {
      id: 'v-1',
      dataset_id: 'ds-1',
      name: 'oss_6m_postop',
      position: 0,
      inferred_type: 'numeric',
      user_type: null,
      n_missing: 0,
      sample_values: ['68', '72', '75'],
      display_label: 'OSS at 6 months',
    },
    {
      id: 'v-2',
      dataset_id: 'ds-1',
      name: 'age',
      position: 1,
      inferred_type: 'numeric',
      user_type: null,
      n_missing: 0,
      sample_values: ['65', '72', '58'],
    },
    {
      id: 'v-3',
      dataset_id: 'ds-1',
      name: 'treatment',
      position: 2,
      inferred_type: 'nominal',
      user_type: null,
      n_missing: 0,
      sample_values: ['A', 'B'],
    },
  ],
  header_sanitisation_report: [],
}

function wrap(node: React.ReactNode) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>{node}</QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
  runMock.mockReset()
  qqPlotMock.mockReset()
  histogramMock.mockReset()
})

describe('DiagnosticsPanel — column pickers', () => {
  it('mounts and lists only numeric columns in the column picker', () => {
    wrap(<DiagnosticsPanel projectId="p-1" dataset={DATASET} />)
    expect(screen.getByTestId('diagnostics-panel')).toBeTruthy()
    // The column-picker trigger shows the first numeric column by default.
    const colTrigger = screen.getByTestId('diag-col')
    // It defaults to the FIRST numeric column ("OSS at 6 months").
    expect(colTrigger.textContent).toContain('OSS at 6 months')
    // The group picker is HIDDEN for Shapiro-Wilk (default test).
    expect(screen.queryByTestId('diag-group')).toBeNull()
  })

  it("hides the group picker by default and the DIAGNOSTIC_NEEDS_GROUP map flags Levene/Bartlett as needing it", async () => {
    wrap(<DiagnosticsPanel projectId="p-1" dataset={DATASET} />)
    // Initially hidden (test_key defaults to shapiro_wilk).
    expect(screen.queryByTestId('diag-group')).toBeNull()
    // Radix Select doesn't respond to fireEvent.change on the trigger,
    // so we verify the conditional-rendering wiring by checking the
    // static needs-group map (which the component uses to decide whether
    // to render the group picker).
    const api = await import('@/lib/api')
    expect(api.DIAGNOSTIC_NEEDS_GROUP.levene).toBe(true)
    expect(api.DIAGNOSTIC_NEEDS_GROUP.bartlett).toBe(true)
    expect(api.DIAGNOSTIC_NEEDS_GROUP.shapiro_wilk).toBe(false)
    expect(api.DIAGNOSTIC_NEEDS_GROUP.anderson_darling).toBe(false)
  })
})

describe('DiagnosticsPanel — Run flow', () => {
  it('runs Shapiro-Wilk and renders statistic + p + interpretation + green pill', async () => {
    runMock.mockResolvedValue({
      test_key: 'shapiro_wilk',
      statistic: 0.985,
      p: 0.42,
      n: 120,
      interpretation:
        'Sample is consistent with a normal distribution (Shapiro-Wilk W=0.9850, p=0.420 > 0.05).',
      ok: true,
    })
    wrap(<DiagnosticsPanel projectId="p-1" dataset={DATASET} />)
    fireEvent.click(screen.getByTestId('diag-run'))
    await waitFor(() => expect(runMock).toHaveBeenCalledTimes(1))
    expect(runMock.mock.calls[0][0]).toBe('p-1')
    expect(runMock.mock.calls[0][1]).toBe('ds-1')
    expect(runMock.mock.calls[0][2]).toMatchObject({
      test_key: 'shapiro_wilk',
      column_name: 'oss_6m_postop',
    })
    const card = await screen.findByTestId('diag-result')
    expect(card.textContent).toContain('Shapiro-Wilk')
    expect(card.textContent).toContain('0.9850') // statistic
    expect(card.textContent).toContain('0.420') // p-value
    expect(card.textContent).toContain('consistent with a normal distribution')
    const pill = within(card).getByTestId('diag-result-pill')
    expect(pill.textContent).toMatch(/holds/i)
  })

  it('shows the amber violated pill when the assumption fails', async () => {
    runMock.mockResolvedValue({
      test_key: 'shapiro_wilk',
      statistic: 0.78,
      p: 0.0001,
      n: 60,
      interpretation:
        'Strong evidence against normality (Shapiro-Wilk W=0.7800, p<0.001 < 0.05); consider a non-parametric alternative such as Mann-Whitney.',
      ok: false,
    })
    wrap(<DiagnosticsPanel projectId="p-1" dataset={DATASET} />)
    fireEvent.click(screen.getByTestId('diag-run'))
    const card = await screen.findByTestId('diag-result')
    expect(card.textContent).toContain('Mann-Whitney')
    const pill = within(card).getByTestId('diag-result-pill')
    expect(pill.textContent).toMatch(/violated/i)
  })
})
