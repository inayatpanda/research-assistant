/**
 * Phase D2 — App-level routing smoke test.
 *
 * Boots the App with a MemoryRouter and verifies that navigating to
 * /install lands on the InstallPage hero ("Get Research Assistant").
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'

import App from '@/App'

afterEach(() => cleanup())

describe('App routes', () => {
  it('renders HomePage at "/"', () => {
    render(<App routerOverride="memory" initialEntries={['/']} />)
    expect(
      screen.getByRole('heading', { level: 1, name: /write better medical research/i }),
    ).toBeInTheDocument()
  })

  it('renders InstallPage at "/install"', () => {
    render(<App routerOverride="memory" initialEntries={['/install']} />)
    expect(screen.getByRole('heading', { level: 1, name: /get research assistant/i })).toBeInTheDocument()
  })
})
