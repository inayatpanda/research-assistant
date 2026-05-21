/**
 * Phase M1.1 — Mobile search bar.
 *
 * A wide, finger-friendly input with a leading search glyph and a
 * trailing clear button that appears once there's something to clear.
 * Used by the Learn tab (and reusable for M2's library search).
 */
import { Search, X } from 'lucide-react'
import { useRef } from 'react'

import { cn } from '@/lib/utils'

export type MobileSearchBarProps = {
  value: string
  onChange: (v: string) => void
  placeholder?: string
  /** Test/aria identifier on the input. */
  testId?: string
  className?: string
  /** Optional autoFocus — defaults to false. */
  autoFocus?: boolean
}

export function MobileSearchBar({
  value,
  onChange,
  placeholder = 'Search',
  testId = 'mobile-search',
  className,
  autoFocus,
}: MobileSearchBarProps) {
  const ref = useRef<HTMLInputElement | null>(null)
  return (
    <div className={cn('relative w-full', className)}>
      <Search
        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
        strokeWidth={1.75}
      />
      <input
        ref={ref}
        data-testid={testId}
        aria-label={placeholder}
        type="search"
        autoFocus={autoFocus}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={cn(
          'h-11 w-full rounded-lg border border-border bg-card pl-9 pr-9 text-[14px]',
          'placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/40',
        )}
      />
      {value && (
        <button
          type="button"
          aria-label="Clear search"
          data-testid={`${testId}-clear`}
          onClick={() => {
            onChange('')
            ref.current?.focus()
          }}
          className={cn(
            'absolute right-1.5 top-1/2 inline-flex h-9 w-9 -translate-y-1/2 items-center justify-center',
            'rounded-md text-muted-foreground hover:bg-muted hover:text-foreground',
          )}
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}
