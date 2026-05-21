/**
 * Phase D2 — DocsPage smoke tests.
 *
 * Asserts FAQ entries render and the accordion expand/collapse cycle
 * works (click → answer visible → click again → hidden).
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import DocsPage from '@/pages/DocsPage'

afterEach(() => cleanup())

describe('DocsPage', () => {
  it('renders the FAQ accordion with 12 questions', () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    )
    const accordion = screen.getByTestId('faq-accordion')
    const buttons = accordion.querySelectorAll('button[aria-expanded]')
    expect(buttons).toHaveLength(12)
  })

  it('expands and collapses a FAQ entry on click', async () => {
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    )
    const trigger = screen.getByRole('button', { name: /where does my data live\?/i })
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    await user.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText(/sqlite database under your user-data directory/i)).toBeInTheDocument()
    await user.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
  })
})
