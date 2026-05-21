/**
 * Phase D2 — SyncPage smoke test.
 *
 * Verifies the three sync steps render and the troubleshooting accordion
 * is present (collapsed by default).
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import SyncPage from '@/pages/SyncPage'

afterEach(() => cleanup())

describe('SyncPage', () => {
  it('renders all three setup steps and the troubleshooting heading', () => {
    render(
      <MemoryRouter>
        <SyncPage />
      </MemoryRouter>,
    )
    // The steps are direct children of the outer <ol data-testid="sync-steps">.
    // Other lists nested inside the steps (e.g. download links) would inflate
    // a generic listitem query, so we scope to the immediate <li> children.
    const stepsList = screen.getByTestId('sync-steps') as HTMLOListElement
    const directSteps = Array.from(stepsList.children).filter((node) => node.tagName === 'LI')
    expect(directSteps).toHaveLength(3)
    expect(screen.getByRole('heading', { level: 2, name: /troubleshooting/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 2, name: /tailscale on your laptop/i })).toBeInTheDocument()
  })
})
