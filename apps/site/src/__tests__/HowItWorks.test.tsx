/**
 * Phase D3 — HowItWorks test.
 *
 * Three-step explainer between the hero/trust strip and the deep
 * feature blocks. We only need to make sure all three steps render
 * with their numbered eyebrows.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'

import { HowItWorks } from '@/components/HowItWorks'

afterEach(() => cleanup())

describe('HowItWorks', () => {
  it('renders the three numbered steps', () => {
    render(<HowItWorks />)
    const steps = screen.getAllByTestId('how-it-works-step')
    expect(steps).toHaveLength(3)
    expect(steps[0]).toHaveTextContent(/01/)
    expect(steps[0]).toHaveTextContent(/Write locally/)
    expect(steps[1]).toHaveTextContent(/02/)
    expect(steps[1]).toHaveTextContent(/Sync via Tailscale/)
    expect(steps[2]).toHaveTextContent(/03/)
    expect(steps[2]).toHaveTextContent(/Share with co-authors/)
  })
})
