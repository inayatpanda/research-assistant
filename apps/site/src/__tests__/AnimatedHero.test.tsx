/**
 * Phase v0.3 — AnimatedHero smoke test.
 *
 * The headline is split into word-level spans so framer-motion can
 * stagger them, but a sub-string assertion on the full heading still
 * works because React's accessible-name algorithm concatenates the
 * inline spans.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import { AnimatedHero } from '@/components/AnimatedHero'

afterEach(() => cleanup())

describe('AnimatedHero', () => {
  it('renders the headline (assembled from word-level spans)', () => {
    render(
      <MemoryRouter>
        <AnimatedHero />
      </MemoryRouter>,
    )
    const heading = screen.getByRole('heading', { level: 1 })
    expect(heading.textContent).toMatch(/local-first/i)
    expect(heading.textContent).toMatch(/manuscript tool/i)
    expect(heading.textContent).toMatch(/clinical research/i)
  })

  it('renders both CTAs and the hero screenshot', () => {
    render(
      <MemoryRouter>
        <AnimatedHero />
      </MemoryRouter>,
    )
    expect(screen.getByTestId('hero-primary-cta')).toHaveAttribute('href', '/signup')
    expect(screen.getByTestId('hero-secondary-cta')).toHaveAttribute('href', '#features')
    expect(screen.getByTestId('hero-screenshot')).toHaveAttribute(
      'src',
      '/screenshots/manuscript@2x.png',
    )
  })
})
