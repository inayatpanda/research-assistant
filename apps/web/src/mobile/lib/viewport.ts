/**
 * Phase M0.4 — viewport hooks.
 *
 * ``useViewport()`` subscribes to ``resize`` + ``orientationchange`` and
 * returns the current window dimensions (throttled to ~100ms so the
 * hook never pegs the main thread during a continuous resize drag).
 *
 * ``useIsMobile()`` returns ``true`` when the viewport width is below
 * 900px (the locked breakpoint from the build plan) AND the user
 * hasn't opted into the "force desktop" toggle.
 *
 * Both hooks are SSR-safe: when ``window`` is undefined they fall back
 * to ``{ width: 0, height: 0 }`` / ``false`` respectively. The vitest
 * default environment is jsdom (which *does* expose ``window``), so we
 * still exercise the real subscription code paths in tests.
 */
import { useEffect, useRef, useState } from 'react'

import { useForceDesktop } from './forceDesktop'

/** Locked from the plan — `<900px` is the mobile breakpoint. */
export const MOBILE_BREAKPOINT_PX = 900

/** Throttle interval for viewport updates. ~10 Hz is plenty for layout. */
export const VIEWPORT_THROTTLE_MS = 100

type Viewport = { width: number; height: number }

function getCurrentViewport(): Viewport {
  if (typeof window === 'undefined') return { width: 0, height: 0 }
  return { width: window.innerWidth, height: window.innerHeight }
}

/**
 * Returns the current window dimensions. Re-renders at most every
 * ``VIEWPORT_THROTTLE_MS`` milliseconds during a continuous resize.
 *
 * Trailing edge: a final update is always scheduled so the captured
 * dimensions match the post-drag viewport (avoids the classic "missed
 * the last few pixels" off-by-one).
 */
export function useViewport(): Viewport {
  const [size, setSize] = useState<Viewport>(() => getCurrentViewport())
  // Track the most recent timer + last-emit timestamp so we can both
  // throttle the leading edge and guarantee a trailing-edge update.
  const lastEmitRef = useRef<number>(0)
  const pendingRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (typeof window === 'undefined') return

    function emit() {
      lastEmitRef.current = Date.now()
      pendingRef.current = null
      setSize(getCurrentViewport())
    }

    function onResize() {
      const now = Date.now()
      const elapsed = now - lastEmitRef.current
      if (elapsed >= VIEWPORT_THROTTLE_MS) {
        // Leading edge — emit immediately.
        if (pendingRef.current) {
          clearTimeout(pendingRef.current)
          pendingRef.current = null
        }
        emit()
      } else if (!pendingRef.current) {
        // Trailing edge — schedule one final emit at the throttle boundary.
        pendingRef.current = setTimeout(emit, VIEWPORT_THROTTLE_MS - elapsed)
      }
    }

    window.addEventListener('resize', onResize)
    window.addEventListener('orientationchange', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      window.removeEventListener('orientationchange', onResize)
      if (pendingRef.current) {
        clearTimeout(pendingRef.current)
        pendingRef.current = null
      }
    }
  }, [])

  return size
}

/**
 * Returns ``true`` when the mobile shell should render. The check is
 * "viewport narrower than 900px AND the user hasn't forced desktop".
 *
 * The force-desktop toggle wins so power users on an iPad can opt out
 * of the simplified mobile UI even when the viewport says otherwise.
 *
 * Returns ``false`` on the server (no window means no mobile).
 */
export function useIsMobile(): boolean {
  const { width } = useViewport()
  const forceDesktop = useForceDesktop((s) => s.enabled)
  if (typeof window === 'undefined') return false
  if (forceDesktop) return false
  return width > 0 && width < MOBILE_BREAKPOINT_PX
}
