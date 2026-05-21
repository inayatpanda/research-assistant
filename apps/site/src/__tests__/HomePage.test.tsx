/**
 * Phase D2 — HomePage smoke tests.
 *
 * Asserts the hero copy, primary CTA, and that all eight feature cards
 * appear. The features grid is the meat of the landing-page sell, so we
 * keep a hard assertion that every one renders.
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
  it('renders the hero headline and subtitle', () => {
    renderHome()
    expect(
      screen.getByRole('heading', { level: 1, name: /write better medical research, faster\./i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/local-first manuscript assistant for clinical research/i)).toBeInTheDocument()
  })

  it('renders all eight feature cards', () => {
    renderHome()
    const features = [
      'Library',
      'Reader',
      'Manuscript editor',
      'Statistics',
      'Meta-analysis',
      'Peer Review',
      'Submission',
      'Mobile PWA',
    ]
    for (const title of features) {
      expect(screen.getByRole('heading', { level: 3, name: title })).toBeInTheDocument()
    }
  })
})
