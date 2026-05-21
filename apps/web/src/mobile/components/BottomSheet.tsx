/**
 * Phase M1.1 — BottomSheet primitive.
 *
 * A slide-up sheet anchored to the bottom of the viewport. Used by:
 *   - Walkthrough TOC ("On this page")
 *   - Project picker in Peer Review
 *   - "About this app" version info dialog
 *
 * Behaviour:
 *   - Backdrop fades in / sheet slides up via framer-motion.
 *   - Drag handle at the top; swipe-down past 80px → closes the sheet.
 *   - Focus is trapped while the sheet is open (Tab / Shift+Tab cycle
 *     within the sheet, mirroring radix-dialog semantics) and the first
 *     focusable child receives focus on mount.
 *   - Optional snap points (e.g. ['50%', '90%']) — only used for the
 *     initial height; we don't animate between snaps in M1.
 *   - role="dialog" + aria-modal="true" so screen readers announce it.
 *
 * NOTE: We deliberately avoid radix-dialog here because it pulls in
 * focus-trap shenanigans that fight the swipe-to-close gesture. A
 * hand-rolled implementation is ~60 LOC and behaves predictably.
 */
import { AnimatePresence, motion, type PanInfo } from 'framer-motion'
import { useCallback, useEffect, useRef } from 'react'

import { cn } from '@/lib/utils'

export type BottomSheetProps = {
  open: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  /** Snap heights as CSS values, e.g. ["50%", "90%"]. */
  snapPoints?: string[]
  /** Index into `snapPoints` to use as the initial height. */
  defaultSnap?: number
  /** Extra class for the outer sheet element. */
  className?: string
}

const SWIPE_CLOSE_PX = 80

export function BottomSheet({
  open,
  onClose,
  title,
  children,
  snapPoints = ['90%'],
  defaultSnap = 0,
  className,
}: BottomSheetProps) {
  const sheetRef = useRef<HTMLDivElement | null>(null)
  const height = snapPoints[Math.max(0, Math.min(defaultSnap, snapPoints.length - 1))]

  // Focus management — on open, push focus into the first tabbable
  // descendant. On close (open → false), restore focus to whatever
  // element had it before.
  const previousFocusRef = useRef<HTMLElement | null>(null)
  useEffect(() => {
    if (!open) return
    previousFocusRef.current = document.activeElement as HTMLElement | null
    // Defer one frame so the AnimatePresence child has mounted before
    // we go looking for tabbable descendants.
    const id = window.requestAnimationFrame(() => {
      const root = sheetRef.current
      if (!root) return
      const first = root.querySelector<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      )
      if (first) first.focus()
      else root.focus()
    })
    return () => {
      window.cancelAnimationFrame(id)
      previousFocusRef.current?.focus?.()
    }
  }, [open])

  // Escape key closes the sheet.
  useEffect(() => {
    if (!open) return
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.stopPropagation()
        onClose()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, onClose])

  // Trap focus inside the sheet — Tab and Shift+Tab cycle through
  // descendants only. Falls back to the sheet container itself if no
  // tabbable children are found.
  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key !== 'Tab') return
      const root = sheetRef.current
      if (!root) return
      const focusable = Array.from(
        root.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      )
      if (focusable.length === 0) {
        e.preventDefault()
        root.focus()
        return
      }
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement as HTMLElement | null
      if (e.shiftKey) {
        if (active === first || !root.contains(active)) {
          e.preventDefault()
          last.focus()
        }
      } else {
        if (active === last) {
          e.preventDefault()
          first.focus()
        }
      }
    },
    [],
  )

  // Drag handler — close if the user pulls down further than the
  // threshold OR releases with a high downward velocity.
  function onDragEnd(_: unknown, info: PanInfo) {
    if (info.offset.y > SWIPE_CLOSE_PX || info.velocity.y > 600) {
      onClose()
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <div
          data-testid="bottom-sheet-root"
          className="fixed inset-0 z-50"
          // Stop propagation so taps inside the backdrop region don't
          // hit underlying tab bars before our handler fires.
          onMouseDown={(e) => e.stopPropagation()}
        >
          <motion.div
            data-testid="bottom-sheet-backdrop"
            className="absolute inset-0 bg-black/40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            onClick={onClose}
          />
          <motion.div
            ref={sheetRef}
            data-testid="bottom-sheet"
            role="dialog"
            aria-modal="true"
            aria-label={title ?? 'Sheet'}
            tabIndex={-1}
            onKeyDown={onKeyDown}
            className={cn(
              'absolute inset-x-0 bottom-0 flex flex-col',
              'rounded-t-2xl border-t border-border bg-background shadow-2xl',
              'pb-[env(safe-area-inset-bottom)]',
              'focus:outline-none',
              className,
            )}
            style={{ height }}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 32, stiffness: 320 }}
            drag="y"
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0, bottom: 0.5 }}
            onDragEnd={onDragEnd}
          >
            {/* Drag handle */}
            <div
              data-testid="bottom-sheet-handle"
              className="flex shrink-0 cursor-grab justify-center py-3 active:cursor-grabbing"
            >
              <div className="h-1.5 w-10 rounded-full bg-muted-foreground/40" />
            </div>
            {title && (
              <div className="shrink-0 px-4 pb-2 text-[15px] font-semibold tracking-tight">
                {title}
              </div>
            )}
            <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pb-4">
              {children}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
