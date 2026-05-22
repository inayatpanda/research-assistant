/**
 * Phase M2.2 — SelectionHandles.
 *
 * Two draggable circular handles ("anchor" + "focus") that bracket a
 * word-level selection in the touch-native mobile reader. They render
 * at absolute positions inside the reader's relative-positioned text
 * container — the parent is responsible for translating word indices
 * → pixel coordinates.
 *
 * The component is purposely thin: it owns the drag gesture but not
 * the selection state. Each handle fires ``onMove(side, clientX,
 * clientY)`` continuously during ``pointermove``; the parent maps the
 * pointer position to the nearest word and updates its ``[start,
 * end]`` range. The handles redraw themselves whenever the parent
 * passes fresh ``anchor`` / ``focus`` coordinates.
 *
 * Pointer events are used (not touch events) because:
 *   - they unify mouse + touch + stylus,
 *   - they fire even when the pointer leaves the original target (via
 *     ``setPointerCapture``), which is essential for a smooth drag,
 *   - they're now supported on every browser the PWA cares about.
 */
import { useCallback } from 'react'

import { cn } from '@/lib/utils'

export type HandleSide = 'anchor' | 'focus'

export type SelectionHandlesProps = {
  /** Pixel position of the start handle, relative to the container. */
  anchor: { x: number; y: number; lineHeight: number } | null
  /** Pixel position of the end handle, relative to the container. */
  focus: { x: number; y: number; lineHeight: number } | null
  /** Fires continuously during a drag. */
  onMove: (side: HandleSide, clientX: number, clientY: number) => void
  /** Fires once when a drag ends — parent can commit / animate / etc. */
  onMoveEnd?: () => void
  className?: string
}

export function SelectionHandles({
  anchor,
  focus,
  onMove,
  onMoveEnd,
  className,
}: SelectionHandlesProps) {
  const onPointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      // Capture the pointer so subsequent ``pointermove`` events fire
      // on this element even if the user's finger drifts off-screen
      // or onto a different word span.
      e.currentTarget.setPointerCapture(e.pointerId)
      // Prevent the parent text from registering simultaneous touch
      // gestures (long-press, scroll) while a handle is in flight.
      e.stopPropagation()
      e.preventDefault()
    },
    [],
  )

  const onPointerMove = useCallback(
    (side: HandleSide) =>
      (e: React.PointerEvent<HTMLDivElement>) => {
        if (!e.currentTarget.hasPointerCapture(e.pointerId)) return
        onMove(side, e.clientX, e.clientY)
      },
    [onMove],
  )

  const onPointerUp = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      // Fix-13/8: explicitly release the pointer capture that
      // ``onPointerDown`` set. Without this, an interrupted gesture
      // (iOS edge-swipe-back, OS gesture-cancel, page hide) leaves
      // the element silently holding the pointer; subsequent
      // selections never fire because the previous capture is still
      // alive.
      try {
        if (e.currentTarget.hasPointerCapture(e.pointerId)) {
          e.currentTarget.releasePointerCapture(e.pointerId)
        }
      } catch {
        /* releasePointerCapture can throw if the capture was lost */
      }
      onMoveEnd?.()
    },
    [onMoveEnd],
  )

  return (
    <>
      {anchor && (
        <div
          data-testid="selection-handle-anchor"
          data-side="anchor"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove('anchor')}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          style={{
            position: 'absolute',
            // Centre the 24pt circle on the start of the first word.
            left: anchor.x - 12,
            top: anchor.y + anchor.lineHeight - 4,
            touchAction: 'none',
          }}
          className={cn(
            'pointer-events-auto z-20 h-6 w-6 rounded-full bg-sky-500 shadow-md',
            'ring-2 ring-background',
            className,
          )}
        />
      )}
      {focus && (
        <div
          data-testid="selection-handle-focus"
          data-side="focus"
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove('focus')}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          style={{
            position: 'absolute',
            // Place the second circle at the trailing edge of the last
            // word's bounding box.
            left: focus.x - 12,
            top: focus.y + focus.lineHeight - 4,
            touchAction: 'none',
          }}
          className={cn(
            'pointer-events-auto z-20 h-6 w-6 rounded-full bg-sky-500 shadow-md',
            'ring-2 ring-background',
            className,
          )}
        />
      )}
    </>
  )
}
