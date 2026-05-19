import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { calculateMock } = vi.hoisted(() => ({
  calculateMock: vi.fn(),
}))

vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>()
  return {
    ...actual,
    powerApi: { calculate: calculateMock },
  }
})

import { PowerCalculator } from '../PowerCalculator'

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
  calculateMock.mockReset()
})

describe('PowerCalculator — happy path', () => {
  beforeEach(() => {
    calculateMock.mockResolvedValue({
      required_n: 128,
      required_n_per_group: 64,
      alpha: 0.05,
      power: 0.8,
      effect_size: 0.5,
      sensitivity_curve_png: 'data:image/png;base64,IMG',
      notes: 'two-sided',
    })
  })

  it('submits the form and renders required-n and sensitivity-curve image', async () => {
    wrap(<PowerCalculator />)
    fireEvent.click(screen.getByRole('button', { name: /calculate/i }))
    await waitFor(() => expect(calculateMock).toHaveBeenCalledTimes(1))
    expect(calculateMock.mock.calls[0][0]).toMatchObject({
      test_family: 'ttest_ind',
      effect_size: 0.5,
      alpha: 0.05,
      power: 0.8,
    })
    const requiredN = await screen.findByTestId('power-required-n')
    expect(requiredN.textContent).toContain('n = 128')
    const img = screen.getByTestId('power-sensitivity-curve') as HTMLImageElement
    expect(img.src).toContain('data:image/png;base64,IMG')
  })
})

describe('PowerCalculator — form validation', () => {
  it('shows an inline error when effect size is non-positive', async () => {
    wrap(<PowerCalculator />)
    const effect = screen.getByTestId('power-effect-size') as HTMLInputElement
    fireEvent.change(effect, { target: { value: '0' } })
    fireEvent.click(screen.getByRole('button', { name: /calculate/i }))
    const alert = await screen.findByRole('alert')
    expect(alert.textContent?.toLowerCase()).toContain('effect size')
    expect(calculateMock).not.toHaveBeenCalled()
  })

  it('rejects α ≥ 1', async () => {
    wrap(<PowerCalculator />)
    const alpha = screen.getByLabelText('α') as HTMLInputElement
    fireEvent.change(alpha, { target: { value: '2' } })
    fireEvent.click(screen.getByRole('button', { name: /calculate/i }))
    const alert = await screen.findByRole('alert')
    expect(alert.textContent).toMatch(/α/)
    expect(calculateMock).not.toHaveBeenCalled()
  })
})
