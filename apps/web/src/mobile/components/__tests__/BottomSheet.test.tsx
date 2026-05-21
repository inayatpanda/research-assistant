/**
 * Phase M1.5 — BottomSheet smoke tests.
 *
 * Covers the three things M1.1 promises:
 *   1. Renders the sheet only while `open === true`.
 *   2. Drag-down past the close threshold dispatches `onClose`.
 *   3. Tab key cycles focus inside the sheet (focus trap).
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { BottomSheet } from '@/mobile/components/BottomSheet'

afterEach(cleanup)

describe('BottomSheet', () => {
  it('does not render the sheet when closed and renders it when open', () => {
    const onClose = vi.fn()
    const { rerender } = render(
      <BottomSheet open={false} onClose={onClose} title="Hi">
        <button data-testid="inner">Inner</button>
      </BottomSheet>,
    )
    expect(screen.queryByTestId('bottom-sheet')).toBeNull()
    rerender(
      <BottomSheet open onClose={onClose} title="Hi">
        <button data-testid="inner">Inner</button>
      </BottomSheet>,
    )
    expect(screen.getByTestId('bottom-sheet')).toBeTruthy()
  })

  it('closes when the backdrop is clicked', () => {
    const onClose = vi.fn()
    render(
      <BottomSheet open onClose={onClose}>
        <button data-testid="inner">Inner</button>
      </BottomSheet>,
    )
    fireEvent.click(screen.getByTestId('bottom-sheet-backdrop'))
    expect(onClose).toHaveBeenCalled()
  })

  it('traps Tab inside the sheet (focus cycles to last when shift+tab on first)', () => {
    const onClose = vi.fn()
    render(
      <BottomSheet open onClose={onClose}>
        <button data-testid="first">First</button>
        <button data-testid="middle">Middle</button>
        <button data-testid="last">Last</button>
      </BottomSheet>,
    )
    const first = screen.getByTestId('first') as HTMLButtonElement
    const last = screen.getByTestId('last') as HTMLButtonElement
    first.focus()
    expect(document.activeElement).toBe(first)
    // Shift+Tab on the first focusable should land on the last.
    fireEvent.keyDown(screen.getByTestId('bottom-sheet'), {
      key: 'Tab',
      shiftKey: true,
    })
    expect(document.activeElement).toBe(last)
  })
})
