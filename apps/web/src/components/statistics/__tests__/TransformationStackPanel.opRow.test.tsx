/**
 * DEMO-FIX-D MEDIUM-3 — Op-stack rows must render ``<output> = <op>(<input>)``
 * for log/z/mutate, ``filter: <expr>`` for filter, and ``recode <col>: <map>``
 * for recode. Pre-fix the log_transform row only showed the input column.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { TransformationRead } from '@/lib/api'
import { TransformationStackPanel } from '@/components/statistics/TransformationStackPanel'

function makeItem(
  op_type: TransformationRead['op_type'],
  op_args: Record<string, unknown>,
): TransformationRead {
  return {
    id: `t-${op_type}-${Math.random().toString(36).slice(2, 7)}`,
    dataset_id: 'ds-1',
    op_type,
    op_args,
    label: null,
    position: 0,
    created_at: '2026-05-18T00:00:00Z',
    updated_at: '2026-05-18T00:00:00Z',
  } as TransformationRead
}

const ITEMS: TransformationRead[] = [
  makeItem('log_transform', {
    column: 'vas_pain_6m_postop',
    new_column: 'log_vas_pain_6m_postop',
    base: 'e',
  }),
  makeItem('z_score', { column: 'score' }),
  makeItem('mutate', {
    new_column: 'bmi_squared',
    expression: 'bmi * bmi',
  }),
  makeItem('filter', { expr: "bmi_group == 'high_bmi'" }),
  makeItem('recode', {
    column: 'arm',
    mapping: { A: 'placebo', B: 'drug' },
  }),
]

vi.mock('@/hooks/useTransformations', async (importOriginal) => {
  const actual = await importOriginal<
    typeof import('@/hooks/useTransformations')
  >()
  return {
    ...actual,
    useTransformations: () => ({ data: ITEMS, isLoading: false }),
    useAddTransformation: () => ({ mutate: vi.fn(), isPending: false }),
    useDeleteTransformation: () => ({ mutate: vi.fn(), isPending: false }),
    useReorderTransformations: () => ({ mutate: vi.fn(), isPending: false }),
    useUpdateTransformation: () => ({ mutate: vi.fn(), isPending: false }),
  }
})

function renderPanel() {
  const qc = new QueryClient()
  return render(
    <QueryClientProvider client={qc}>
      <TransformationStackPanel projectId="p-1" datasetId="ds-1" />
    </QueryClientProvider>,
  )
}

afterEach(() => {
  cleanup()
})

describe('TransformationStackPanel op-row summary', () => {
  it('log_transform shows "<new> = log(<input>)"', () => {
    const { getByText } = renderPanel()
    expect(
      getByText('log_vas_pain_6m_postop = log(vas_pain_6m_postop)'),
    ).toBeTruthy()
  })

  it('z_score derives default output name "z_<col>"', () => {
    const { getByText } = renderPanel()
    expect(getByText('z_score = z(score)')).toBeTruthy()
  })

  it('mutate shows "<new> = <expression>"', () => {
    const { getByText } = renderPanel()
    expect(getByText('bmi_squared = bmi * bmi')).toBeTruthy()
  })

  it('filter (expr shape) shows "filter: <expr>"', () => {
    const { getByText } = renderPanel()
    expect(getByText(/filter:\s+bmi_group == 'high_bmi'/)).toBeTruthy()
  })

  it('recode shows "recode <col>: <a→x, b→y>"', () => {
    const { getByText } = renderPanel()
    expect(getByText(/recode arm:\s+A→placebo, B→drug/)).toBeTruthy()
  })
})
