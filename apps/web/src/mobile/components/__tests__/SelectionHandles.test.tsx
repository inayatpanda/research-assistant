/**
 * Phase M2.3 — SelectionHandles smoke tests.
 *
 *   1. Both handles render when anchor + focus props are supplied.
 *   2. Dragging the focus handle fires onMove(side, x, y).
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { SelectionHandles } from '@/mobile/components/SelectionHandles'

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('SelectionHandles', () => {
  it('renders both anchor + focus handles when positions are provided', () => {
    render(
      <SelectionHandles
        anchor={{ x: 10, y: 20, lineHeight: 24 }}
        focus={{ x: 100, y: 20, lineHeight: 24 }}
        onMove={() => {}}
      />,
    )
    expect(screen.getByTestId('selection-handle-anchor')).toBeTruthy()
    expect(screen.getByTestId('selection-handle-focus')).toBeTruthy()
  })

  it('drag on the focus handle fires onMove with new coordinates', () => {
    const onMove = vi.fn()
    render(
      <SelectionHandles
        anchor={{ x: 10, y: 20, lineHeight: 24 }}
        focus={{ x: 100, y: 20, lineHeight: 24 }}
        onMove={onMove}
      />,
    )
    const handle = screen.getByTestId('selection-handle-focus') as HTMLElement
    // jsdom doesn't implement setPointerCapture by default — stub it.
    ;(handle as unknown as { setPointerCapture: (id: number) => void }).setPointerCapture =
      vi.fn()
    ;(handle as unknown as { hasPointerCapture: (id: number) => boolean }).hasPointerCapture =
      vi.fn().mockReturnValue(true)

    fireEvent.pointerDown(handle, { pointerId: 1, clientX: 100, clientY: 30 })
    fireEvent.pointerMove(handle, { pointerId: 1, clientX: 180, clientY: 30 })
    expect(onMove).toHaveBeenCalled()
    const [side, x, y] = onMove.mock.calls.at(-1)!
    expect(side).toBe('focus')
    expect(x).toBe(180)
    expect(y).toBe(30)
  })
})
