/**
 * Phase D3 — Hero component test.
 *
 * The hero is the home page's most important block (above-fold copy +
 * CTAs). Make sure both CTAs render and link to the expected routes
 * so a refactor can't silently break the conversion path.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import { Hero } from '@/components/Hero'

afterEach(() => cleanup())

describe('Hero', () => {
  it('renders the headline and both CTAs', () => {
    render(
      <MemoryRouter>
        <Hero />
      </MemoryRouter>,
    )
    expect(
      screen.getByRole('heading', { level: 1, name: /local-first/i }),
    ).toBeInTheDocument()
    const primary = screen.getByTestId('hero-primary-cta')
    const secondary = screen.getByTestId('hero-secondary-cta')
    expect(primary).toHaveAttribute('href', '/signup')
    expect(secondary).toHaveAttribute('href', '#features')
  })

  it('embeds the manuscript hero screenshot', () => {
    render(
      <MemoryRouter>
        <Hero />
      </MemoryRouter>,
    )
    const img = screen.getByTestId('hero-screenshot') as HTMLImageElement
    expect(img).toBeInTheDocument()
    expect(img).toHaveAttribute('src', '/screenshots/manuscript@2x.png')
  })
})
