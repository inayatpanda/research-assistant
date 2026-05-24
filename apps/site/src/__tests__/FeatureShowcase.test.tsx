/**
 * Phase v0.3 — FeatureShowcase component tests.
 *
 * Covers:
 *   - Renders all seven tabs.
 *   - Clicking a tab updates the active screenshot + url bar + aria-selected.
 *   - Auto-rotation advances after AUTO_ROTATE_MS when no manual select.
 */
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, it, expect, vi } from 'vitest'

import { FeatureShowcase } from '@/components/FeatureShowcase'

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

describe('FeatureShowcase', () => {
  it('renders all seven tabs', () => {
    render(<FeatureShowcase />)
    const ids = [
      'library',
      'reader',
      'manuscript',
      'statistics',
      'meta-analysis',
      'peer-review',
      'submission',
    ]
    for (const id of ids) {
      expect(screen.getByTestId(`showcase-tab-${id}`)).toBeInTheDocument()
    }
  })

  it('starts with the library tab selected', () => {
    render(<FeatureShowcase />)
    const libraryTab = screen.getByTestId('showcase-tab-library')
    expect(libraryTab).toHaveAttribute('aria-selected', 'true')
    const screenshot = screen.getByTestId('showcase-screenshot') as HTMLImageElement
    expect(screenshot.getAttribute('data-active-id')).toBe('library')
  })

  it('switches active tab on click and updates the url bar', () => {
    render(<FeatureShowcase />)
    const submissionTab = screen.getByTestId('showcase-tab-submission')
    fireEvent.click(submissionTab)
    expect(submissionTab).toHaveAttribute('aria-selected', 'true')
    const libraryTab = screen.getByTestId('showcase-tab-library')
    expect(libraryTab).toHaveAttribute('aria-selected', 'false')
    expect(screen.getByTestId('showcase-url-bar').textContent).toMatch(/submission/i)
  })

  it('auto-rotates away from the initial tab after the 5s interval fires', async () => {
    vi.useFakeTimers()
    render(<FeatureShowcase />)
    expect(screen.getByTestId('showcase-tab-library')).toHaveAttribute(
      'aria-selected',
      'true',
    )
    // Drive the 60 ms interval forward past 5 s. fake-timers + async
    // act will flush all queued React state updates; in practice this
    // can advance more than one tab (because once activeIdx changes
    // the effect re-runs with a fresh interval that the remaining
    // 200 ms ticks against). We only assert that auto-rotation has
    // moved off library.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5200)
    })
    expect(screen.getByTestId('showcase-tab-library')).toHaveAttribute(
      'aria-selected',
      'false',
    )
    // Exactly one tab is selected at any time.
    const selected = screen
      .getByTestId('showcase-tablist')
      .querySelectorAll('[aria-selected="true"]')
    expect(selected.length).toBe(1)
  })
})
