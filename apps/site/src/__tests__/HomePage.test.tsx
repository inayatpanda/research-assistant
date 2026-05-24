/**
 * Phase D3 — HomePage redesign smoke tests.
 *
 * The home page is now composed from a hero, trust strip, how-it-works,
 * seven feature sections, the architecture diagram, a pricing teaser
 * and a closing CTA. These tests assert that all of those scaffold
 * pieces render — they're regression bait, not behaviour tests, so
 * they only need to confirm the structure exists.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import HomePage from '@/pages/HomePage'

afterEach(() => cleanup())

function renderHome() {
  return render(
    <MemoryRouter>
      <HomePage />
    </MemoryRouter>,
  )
}

describe('HomePage', () => {
  it('renders the hero headline', () => {
    renderHome()
    expect(
      screen.getByRole('heading', { level: 1, name: /local-first/i }),
    ).toBeInTheDocument()
  })

  it('renders the trust strip with all four signals', () => {
    renderHome()
    const strip = screen.getByTestId('trust-strip')
    expect(strip).toHaveTextContent(/built by clinicians/i)
    expect(strip).toHaveTextContent(/open source/i)
    expect(strip).toHaveTextContent(/no telemetry/i)
    expect(strip).toHaveTextContent(/no subscription/i)
  })

  it('renders all seven feature sections', () => {
    renderHome()
    const ids = [
      'library',
      'reader',
      'manuscript',
      'statistics',
      'peer-review',
      'submission',
      'mobile',
    ]
    for (const id of ids) {
      expect(screen.getByTestId(`feature-section-${id}`)).toBeInTheDocument()
    }
  })

  it('renders the architecture diagram', () => {
    renderHome()
    expect(screen.getByTestId('architecture-diagram')).toBeInTheDocument()
  })

  it('renders both primary and secondary hero CTAs', () => {
    renderHome()
    expect(screen.getByTestId('hero-primary-cta')).toBeInTheDocument()
    expect(screen.getByTestId('hero-secondary-cta')).toBeInTheDocument()
  })

  it('renders the interactive feature showcase right below the hero', () => {
    renderHome()
    expect(screen.getByTestId('feature-showcase')).toBeInTheDocument()
    // Seven tabs, one per app surface.
    expect(screen.getByTestId('showcase-tab-library')).toBeInTheDocument()
    expect(screen.getByTestId('showcase-tab-submission')).toBeInTheDocument()
  })

  it('renders the stat counter row', () => {
    renderHome()
    expect(screen.getByTestId('stat-counter')).toBeInTheDocument()
  })

  it('renders the home FAQ accordion', () => {
    renderHome()
    expect(screen.getByTestId('home-faq')).toBeInTheDocument()
    expect(screen.getByTestId('acc-trigger-local-first')).toBeInTheDocument()
  })
})
