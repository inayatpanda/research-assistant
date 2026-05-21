/**
 * Phase M1.1 — Empty-state widget for mobile pages.
 *
 * Renders a centred icon, title, subtitle and optional CTA button.
 * Used when a list is empty, an API returns no items, or a feature is
 * not yet available on the current device.
 */
import type { LucideIcon } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export type MobileEmptyProps = {
  icon?: LucideIcon
  title: string
  subtitle?: string
  cta?: { label: string; onClick: () => void }
  className?: string
  testId?: string
}

export function MobileEmpty({
  icon: Icon,
  title,
  subtitle,
  cta,
  className,
  testId = 'mobile-empty',
}: MobileEmptyProps) {
  return (
    <div
      data-testid={testId}
      className={cn(
        'flex flex-col items-center justify-center gap-3 px-6 py-16 text-center',
        className,
      )}
    >
      {Icon && (
        <div className="flex h-14 w-14 items-center justify-center rounded-full bg-muted">
          <Icon className="h-6 w-6 text-muted-foreground" strokeWidth={1.5} />
        </div>
      )}
      <div className="text-[15px] font-semibold tracking-tight">{title}</div>
      {subtitle && (
        <div className="max-w-[280px] text-[13px] text-muted-foreground">
          {subtitle}
        </div>
      )}
      {cta && (
        <Button
          type="button"
          onClick={cta.onClick}
          variant="default"
          className="mt-2"
          data-testid={`${testId}-cta`}
        >
          {cta.label}
        </Button>
      )}
    </div>
  )
}
