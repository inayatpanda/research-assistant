import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

// ChartImage uses lazy-loading; stub it out.
vi.mock('@/components/statistics/ChartImage', () => ({
  ChartImage: ({ alt }: { alt: string }) => (
    <div data-testid={`chart-${alt.toLowerCase().replace(/\W+/g, '-')}`}>
      [{alt}]
    </div>
  ),
}))

import { EconomicResultsCard } from '../EconomicResultsCard'
import type { EconomicAnalysis } from '@/lib/api'

function makeAnalysis(
  status: 'dominant' | 'dominated' | 'northeast' | 'southwest',
  overrides: Partial<EconomicAnalysis['result']> = {},
): EconomicAnalysis {
  const result = {
    id: 'r1',
    economic_analysis_id: 'a1',
    mean_cost_diff: status === 'dominant' || status === 'southwest' ? -120.0 : 500.0,
    mean_qaly_diff:
      status === 'dominant' || status === 'northeast' ? 0.15 : -0.05,
    icer: status === 'dominant' || status === 'dominated' ? null : 20_123,
    dominance_status: status,
    nmb_at_thresholds: { '20000': 1500, '30000': 2700 },
    ceac_data: [],
    plane_bootstrap: Array.from({ length: 4 }, (_, i) => ({
      dCost: i * 10,
      dQALY: i * 0.01,
    })),
    sensitivity: null,
    plane_png_uri: 'data:image/png;base64,AAA',
    ceac_png_uri: 'data:image/png;base64,BBB',
    created_at: 'x',
    ...overrides,
  } as NonNullable<EconomicAnalysis['result']>
  return {
    id: 'a1',
    project_id: 'p1',
    dataset_id: 'd1',
    name: 'CRAFFT vs control',
    currency: 'GBP',
    time_horizon_months: 12,
    perspective: 'healthcare_system',
    discount_rate_costs: 0.035,
    discount_rate_qalys: 0.035,
    wtp_thresholds: [20000, 30000],
    utility_value_set: 'EQ5D_5L_UK',
    bootstrap_n: 1000,
    seed: 42,
    treatment_col: 'arm',
    comparator_label: 'control',
    intervention_label: 'anterior',
    cost_columns: [],
    ai_interpretation: null,
    created_at: 'x',
    updated_at: 'x',
    result,
  }
}

describe('EconomicResultsCard', () => {
  afterEach(cleanup)

  it('renders the DOMINANT badge for dominant analyses', () => {
    render(<EconomicResultsCard analysis={makeAnalysis('dominant')} />)
    expect(screen.getByText('dominant')).toBeTruthy()
    // ICER is null when dominant → renders "n/a"
    expect(screen.getByText('n/a')).toBeTruthy()
  })

  it('renders the ICER and per-WTP NMB for NE-quadrant analyses', () => {
    render(<EconomicResultsCard analysis={makeAnalysis('northeast')} />)
    expect(screen.getByText('northeast')).toBeTruthy()
    // ICER appears with currency + /QALY suffix.
    expect(screen.getByText(/£20,123/)).toBeTruthy()
    // Both WTP rows render.
    expect(screen.getByText(/@\s*£20,000/)).toBeTruthy()
    expect(screen.getByText(/@\s*£30,000/)).toBeTruthy()
  })

  it('shows the dominated badge and renders chart placeholders', () => {
    render(<EconomicResultsCard analysis={makeAnalysis('dominated')} />)
    expect(screen.getByText('dominated')).toBeTruthy()
    expect(
      screen.getByTestId('chart-cost-effectiveness-plane'),
    ).toBeTruthy()
    expect(
      screen.getByTestId('chart-cost-effectiveness-acceptability-curve'),
    ).toBeTruthy()
  })

  it('renders a not-yet-run message when result is missing', () => {
    const a = makeAnalysis('northeast')
    a.result = null
    render(<EconomicResultsCard analysis={a} />)
    expect(screen.getByText(/has not been run yet/i)).toBeTruthy()
  })
})
