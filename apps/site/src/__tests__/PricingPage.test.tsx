/**
 * Phase L1c.8 — PricingPage smoke tests.
 *
 * Asserts that both pricing cards render with the expected price tags
 * and that the lifetime CTA links to the Lemon Squeezy checkout URL.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import PricingPage from '@/pages/PricingPage'
import { LEMON_SQUEEZY_CHECKOUT_URL } from '@/lib/licenseApi'

afterEach(() => cleanup())

function renderPricing() {
  return render(
    <MemoryRouter>
      <PricingPage />
    </MemoryRouter>,
  )
}

describe('PricingPage', () => {
  it('renders both pricing cards with the expected prices', () => {
    renderPricing()
    const trial = screen.getByTestId('pricing-card-trial')
    const lifetime = screen.getByTestId('pricing-card-lifetime')
    expect(trial).toBeInTheDocument()
    expect(lifetime).toBeInTheDocument()
    expect(trial.textContent ?? '').toContain('$0')
    expect(lifetime.textContent ?? '').toContain('$29')
  })

  it('points the lifetime CTA at the Lemon Squeezy checkout URL', () => {
    renderPricing()
    const cta = screen.getByTestId('pricing-lifetime-cta') as HTMLAnchorElement
    expect(cta.getAttribute('href')).toBe(LEMON_SQUEEZY_CHECKOUT_URL)
    expect(cta.getAttribute('target')).toBe('_blank')
  })
})
