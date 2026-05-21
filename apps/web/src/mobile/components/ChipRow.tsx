/**
 * Phase M1.1 — Horizontal pill row.
 *
 * Lays out a list of chip-style buttons in a horizontally scrollable
 * row (no scrollbar shown). Used by MobileLearn for the category
 * selector. Each chip is at least 36pt tall so it's comfortable to
 * tap; the active chip flips the accent colour.
 */
import { cn } from '@/lib/utils'

export type ChipRowOption<T extends string = string> = {
  value: T
  label: string
  /** Optional small badge text (e.g. count). */
  badge?: string | number
}

export type ChipRowProps<T extends string = string> = {
  options: ChipRowOption<T>[]
  value: T
  onChange: (v: T) => void
  ariaLabel?: string
  className?: string
  testId?: string
}

export function ChipRow<T extends string = string>({
  options,
  value,
  onChange,
  ariaLabel = 'Filter',
  className,
  testId = 'chip-row',
}: ChipRowProps<T>) {
  return (
    <div
      data-testid={testId}
      role="tablist"
      aria-label={ariaLabel}
      className={cn(
        'flex gap-2 overflow-x-auto px-3 py-2',
        // Hide native scrollbars but keep the swipe affordance.
        '[scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden',
        className,
      )}
    >
      {options.map((opt) => {
        const active = opt.value === value
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={active}
            data-testid={`${testId}-${opt.value}`}
            onClick={() => onChange(opt.value)}
            className={cn(
              'inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full border px-3.5 text-[13px] font-medium transition-colors',
              active
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-card text-muted-foreground hover:text-foreground',
            )}
          >
            <span>{opt.label}</span>
            {opt.badge != null && (
              <span
                className={cn(
                  'inline-flex h-5 min-w-[20px] items-center justify-center rounded-full px-1.5 text-[10px] font-medium',
                  active
                    ? 'bg-primary-foreground/15 text-primary-foreground'
                    : 'bg-muted text-muted-foreground',
                )}
              >
                {opt.badge}
              </span>
            )}
          </button>
        )
      })}
    </div>
  )
}
