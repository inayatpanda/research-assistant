/**
 * Phase v0.3 — StatCounter smoke test.
 *
 * Counter relies on requestAnimationFrame and IntersectionObserver,
 * neither of which fire in jsdom — so we just confirm the row + its
 * five stats render. The counter values will be the initial state
 * (0) which is fine; the visual count-up only matters in the
 * browser.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'

import { StatCounter } from '@/components/StatCounter'

afterEach(() => cleanup())

describe('StatCounter', () => {
  it('renders five stat cells', () => {
    render(<StatCounter />)
    const row = screen.getByTestId('stat-counter')
    expect(row).toBeInTheDocument()
    // The five expected targets in order.
    expect(screen.getByTestId('stat-27')).toBeInTheDocument()
    expect(screen.getByTestId('stat-12')).toBeInTheDocument()
    expect(screen.getByTestId('stat-60')).toBeInTheDocument()
    expect(screen.getByTestId('stat-3')).toBeInTheDocument()
    expect(screen.getByTestId('stat-0')).toBeInTheDocument()
  })

  it('renders the stat labels in the DOM', () => {
    render(<StatCounter />)
    // Each label appears twice: an sr-only <dt> and a visible <span>.
    // We just need to confirm presence — getAllByText covers both.
    expect(screen.getAllByText(/statistical tests/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/reporting checklists/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/cloud dependencies/i).length).toBeGreaterThan(0)
  })
})
