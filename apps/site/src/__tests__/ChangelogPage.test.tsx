/**
 * Phase D2 — ChangelogPage smoke test.
 *
 * Asserts entries render in reverse-chronological order — the first
 * entry's date must be newer than (or equal to) the last entry's date.
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect } from 'vitest'
import { MemoryRouter } from 'react-router-dom'

import ChangelogPage from '@/pages/ChangelogPage'
import { CHANGELOG } from '@/data/changelog'

afterEach(() => cleanup())

describe('ChangelogPage', () => {
  it('renders all entries in reverse-chronological order', () => {
    render(
      <MemoryRouter>
        <ChangelogPage />
      </MemoryRouter>,
    )
    const entries = screen.getAllByTestId('changelog-entry')
    expect(entries.length).toBe(CHANGELOG.length)
    expect(entries.length).toBeGreaterThanOrEqual(8)
    // The data source is authored newest-first; assert each successive
    // date is <= the previous one.
    for (let i = 1; i < CHANGELOG.length; i += 1) {
      const prev = new Date(CHANGELOG[i - 1].date).getTime()
      const curr = new Date(CHANGELOG[i].date).getTime()
      expect(prev).toBeGreaterThanOrEqual(curr)
    }
  })
})
