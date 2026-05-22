/**
 * Phase M0.5 — top-level mobile chrome.
 *
 * Layout:
 *   - sticky <MobileHeader> at the top
 *   - scrollable <main> in the middle, sized to fill the gap between
 *     header and bottom tabs
 *   - fixed <BottomTabs> at the bottom
 *
 * Page transitions:
 *   - we wrap the routed outlet in <AnimatePresence mode="wait">
 *   - each child <motion.div> slides in from the right on forward
 *     navigation, slides out to the left on the reverse
 *   - the direction is inferred from the history `key` — a brand-new
 *     entry means "push" (slide right→centre), revisiting an earlier
 *     entry means "pop" (slide centre→right). framer-motion handles
 *     interpolation; we just supply the variants.
 *
 * Auth: the whole shell is wrapped in <RequireAuth>, so a logged-out
 * user landing on `/m/library` is bounced to `/login` first.
 */
import { useEffect, useMemo, useRef } from 'react'
import { AnimatePresence, motion, type Variants } from 'framer-motion'
import { Outlet, useLocation } from 'react-router-dom'

import { RequireAuth } from '@/components/auth/RequireAuth'
import { useLicenseAccount } from '@/lib/licenseStore'
import { cn } from '@/lib/utils'

import { BottomTabs } from './components/BottomTabs'
import { MobileHeader } from './components/MobileHeader'
import { MOBILE_TABS } from './lib/tabs'

const slideVariants: Variants = {
  enterRight: { x: '100%', opacity: 0 },
  enterLeft: { x: '-100%', opacity: 0 },
  center: {
    x: 0,
    opacity: 1,
    transition: { duration: 0.28, ease: [0.16, 1, 0.3, 1] },
  },
  exitLeft: {
    x: '-100%',
    opacity: 0,
    transition: { duration: 0.22, ease: [0.16, 1, 0.3, 1] },
  },
  exitRight: {
    x: '100%',
    opacity: 0,
    transition: { duration: 0.22, ease: [0.16, 1, 0.3, 1] },
  },
}

/**
 * Compare two history keys: returns -1, 0, or +1. The router assigns
 * monotonically increasing pseudo-random keys, so we compare them
 * lexically as a cheap proxy for "newer entry".
 */
function compareKeys(a: string, b: string): number {
  if (a === b) return 0
  return a > b ? 1 : -1
}

export function MobileShell() {
  return (
    <RequireAuth>
      <MobileShellInner />
    </RequireAuth>
  )
}

function MobileShellInner() {
  const location = useLocation()
  const prevKeyRef = useRef<string>(location.key)
  const licenseAccount = useLicenseAccount()
  const licenseDisplayName = licenseAccount?.display_name ?? ''
  // Derive a stable per-location direction (+1 push / -1 pop) so the
  // exit animation matches the entry animation when the user taps
  // "Back".
  const direction = useMemo(() => {
    const dir = compareKeys(location.key, prevKeyRef.current)
    return dir
  }, [location.key])

  useEffect(() => {
    prevKeyRef.current = location.key
  }, [location.key])

  // Resolve a header title from the active tab. Sub-pages (e.g. a
  // reader inside the library) override the title via their own
  // `<MobileHeader>`; the shell's header is the fallback.
  const activeTab = MOBILE_TABS.find((t) => location.pathname.startsWith(t.path))
  const title = activeTab?.label ?? 'Research'

  return (
    <div
      data-testid="mobile-shell"
      data-license-watermark={licenseDisplayName}
      className="flex min-h-[100dvh] flex-col bg-background"
    >
      <MobileHeader title={title} />
      <main
        className={cn(
          'flex-1 overflow-y-auto overscroll-contain',
          // Pad the bottom by the tab bar height + safe area inset so
          // the last item in a scroll list isn't hidden by the bar.
          'pb-[calc(64px+env(safe-area-inset-bottom))]',
        )}
      >
        <AnimatePresence mode="wait" initial={false} custom={direction}>
          <motion.div
            key={location.pathname}
            custom={direction}
            variants={slideVariants}
            initial={direction >= 0 ? 'enterRight' : 'enterLeft'}
            animate="center"
            exit={direction >= 0 ? 'exitLeft' : 'exitRight'}
            className="min-h-full"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
      <BottomTabs />
    </div>
  )
}

