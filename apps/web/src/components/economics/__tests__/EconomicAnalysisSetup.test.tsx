import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

// Stub the catalogue hook so UtilityValueSetSelector renders synchronously.
vi.mock('@/hooks/useEconomicAnalyses', async (orig) => {
  const real = (await orig()) as Record<string, unknown>
  return {
    ...real,
    useUtilityValueSets: () => ({
      data: [
        {
          key: 'EQ5D_5L_UK',
          label: 'EQ-5D-5L England (Devlin 2018)',
          dimensions: ['mobility'],
          levels: 5,
          source_citation: 'Devlin 2018',
          notes: null,
        },
        {
          key: 'EQ5D_3L_UK',
          label: 'EQ-5D-3L UK (Dolan 1997)',
          dimensions: ['mobility'],
          levels: 3,
          source_citation: 'Dolan 1997',
          notes: null,
        },
      ],
      isLoading: false,
    }),
  }
})

import { EconomicAnalysisSetup } from '../EconomicAnalysisSetup'

describe('EconomicAnalysisSetup', () => {
  afterEach(cleanup)

  it('renders the form fields', () => {
    render(<EconomicAnalysisSetup onSubmit={vi.fn()} />)
    expect(screen.getByTestId('economic-analysis-setup')).toBeTruthy()
    expect(screen.getByLabelText(/Analysis name/i)).toBeTruthy()
    expect(screen.getByLabelText(/WTP thresholds/i)).toBeTruthy()
    expect(screen.getByLabelText(/Treatment column/i)).toBeTruthy()
  })

  it('submits parsed WTP thresholds and labels', () => {
    const onSubmit = vi.fn()
    render(<EconomicAnalysisSetup onSubmit={onSubmit} />)
    fireEvent.change(screen.getByLabelText(/Analysis name/i), {
      target: { value: 'CRAFFT CEA' },
    })
    fireEvent.change(screen.getByLabelText(/WTP thresholds/i), {
      target: { value: '15000, 20000, 30000' },
    })
    fireEvent.change(screen.getByLabelText(/Treatment column/i), {
      target: { value: 'arm' },
    })
    fireEvent.change(screen.getByLabelText(/Intervention label/i), {
      target: { value: 'anterior' },
    })
    fireEvent.change(screen.getByLabelText(/Comparator label/i), {
      target: { value: 'control' },
    })
    fireEvent.click(screen.getByRole('button', { name: /create|continue/i }))

    expect(onSubmit).toHaveBeenCalledTimes(1)
    const body = onSubmit.mock.calls[0][0]
    expect(body.name).toBe('CRAFFT CEA')
    expect(body.wtp_thresholds).toEqual([15000, 20000, 30000])
    expect(body.treatment_col).toBe('arm')
    expect(body.intervention_label).toBe('anterior')
    expect(body.comparator_label).toBe('control')
  })
})
