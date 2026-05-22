/**
 * Fix-13/9 — ConfirmSheet smoke tests.
 *
 *   - renders title + message + buttons when ``open``
 *   - clicking Confirm fires onConfirm
 *   - clicking Cancel fires onCancel
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ConfirmSheet } from '@/mobile/components/ConfirmSheet'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('ConfirmSheet (Fix-13/9)', () => {
  it('renders title, message and confirm/cancel buttons when open', () => {
    render(
      <ConfirmSheet
        open
        title="Delete highlight"
        message="This will remove the highlight."
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    )
    // Title is on the sheet header — assert by aria-label.
    expect(screen.getByRole('dialog', { name: /delete highlight/i })).toBeTruthy()
    expect(
      screen.getByText('This will remove the highlight.'),
    ).toBeTruthy()
    expect(screen.getByTestId('confirm-sheet-confirm').textContent).toMatch(
      /delete/i,
    )
    expect(screen.getByTestId('confirm-sheet-cancel').textContent).toMatch(
      /cancel/i,
    )
  })

  it('fires onConfirm when the Confirm button is tapped', () => {
    const onConfirm = vi.fn()
    render(
      <ConfirmSheet
        open
        title="Delete x"
        message="?"
        onConfirm={onConfirm}
        onCancel={() => {}}
      />,
    )
    fireEvent.click(screen.getByTestId('confirm-sheet-confirm'))
    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('fires onCancel when the Cancel button is tapped', () => {
    const onCancel = vi.fn()
    render(
      <ConfirmSheet
        open
        title="Delete x"
        message="?"
        onConfirm={() => {}}
        onCancel={onCancel}
      />,
    )
    fireEvent.click(screen.getByTestId('confirm-sheet-cancel'))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('does not render when open=false', () => {
    render(
      <ConfirmSheet
        open={false}
        title="Hidden"
        message="x"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    )
    expect(screen.queryByTestId('confirm-sheet')).toBeNull()
  })
})
