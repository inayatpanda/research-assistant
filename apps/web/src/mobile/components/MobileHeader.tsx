/**
 * Phase M0.5 — sticky top header for the mobile shell.
 *
 * 44pt high (the iOS Human Interface Guidelines minimum tap target)
 * with a safe-area inset on top so the title clears the iPhone
 * status bar / notch when installed to home screen.
 *
 * Slots:
 *   - left:  optional back button rendered automatically when ``onBack`` is set
 *   - title: short page title
 *   - right: caller-supplied action button (e.g. a "Save" or filter icon)
 */
import type { ReactNode } from 'react'
import { ChevronLeft } from 'lucide-react'

import { cn } from '@/lib/utils'

export type MobileHeaderProps = {
  title: string
  /** When set, the header renders a back chevron that calls this handler. */
  onBack?: () => void
  /** Optional right-side slot for a single action (icon button etc.). */
  right?: ReactNode
  /** Extra class name(s) applied to the outer element. */
  className?: string
}

export function MobileHeader({ title, onBack, right, className }: MobileHeaderProps) {
  return (
    <header
      data-testid="mobile-header"
      className={cn(
        'sticky top-0 z-30 w-full bg-background/95 backdrop-blur',
        'border-b border-border',
        // Safe-area top inset + visual padding. The 44pt body sits below
        // ``env(safe-area-inset-top)`` so iOS notches/punch-holes are
        // never overlapped by the title.
        'pt-[env(safe-area-inset-top)]',
        className,
      )}
    >
      <div className="flex h-11 items-center justify-between px-3">
        <div className="flex w-12 justify-start">
          {onBack ? (
            <button
              type="button"
              aria-label="Go back"
              onClick={onBack}
              className={cn(
                'inline-flex h-11 w-11 items-center justify-center',
                '-ml-2 rounded-md text-foreground hover:bg-muted',
              )}
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
          ) : null}
        </div>
        <h1 className="truncate text-[16px] font-semibold tracking-tight">
          {title}
        </h1>
        <div className="flex w-12 justify-end">{right ?? null}</div>
      </div>
    </header>
  )
}
