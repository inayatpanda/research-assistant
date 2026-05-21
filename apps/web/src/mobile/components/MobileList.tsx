/**
 * Phase M1.1 — Generic mobile list + list-row.
 *
 * Touch-friendly: each row is at least 56pt tall (well above HIG's
 * 44pt minimum) so people with stubby fingers can hit it on a small
 * screen. Rows are full-width buttons with an icon slot, title +
 * optional subtitle and a trailing chevron.
 *
 * Usage:
 *   <MobileList>
 *     <MobileListRow icon={Foo} title="Account" onClick={...} />
 *     ...
 *   </MobileList>
 *
 * The wrapper renders a vertically stacked rounded card so the rows
 * blend with the rest of the mobile UI shadcn-card aesthetic. Use the
 * `groupTitle` prop on the wrapper to render a small section heading
 * above the card (matches the iOS Settings app pattern).
 */
import { ChevronRight, type LucideIcon } from 'lucide-react'
import * as React from 'react'

import { cn } from '@/lib/utils'

export type MobileListProps = {
  children: React.ReactNode
  /** Optional uppercase section heading (e.g. "Account"). */
  groupTitle?: string
  className?: string
}

export function MobileList({ children, groupTitle, className }: MobileListProps) {
  return (
    <div className={cn('space-y-1.5', className)}>
      {groupTitle && (
        <div
          data-testid="mobile-list-group-title"
          className="px-4 pt-2 text-[11px] uppercase tracking-wider text-muted-foreground font-medium"
        >
          {groupTitle}
        </div>
      )}
      <div
        data-testid="mobile-list"
        className="mx-3 divide-y divide-border rounded-xl border border-border bg-card"
      >
        {children}
      </div>
    </div>
  )
}

export type MobileListRowProps = {
  /** Optional leading icon component. */
  icon?: LucideIcon
  title: React.ReactNode
  subtitle?: React.ReactNode
  /** Replaces the default trailing chevron when provided. */
  trailing?: React.ReactNode
  onClick?: () => void
  /** Render as a non-interactive row (no chevron, no hover). */
  static?: boolean
  className?: string
  'data-testid'?: string
}

export function MobileListRow({
  icon: Icon,
  title,
  subtitle,
  trailing,
  onClick,
  static: isStatic,
  className,
  'data-testid': dataTestId,
}: MobileListRowProps) {
  const isButton = !isStatic && !!onClick
  const Element = isButton ? 'button' : 'div'
  return (
    <Element
      data-testid={dataTestId}
      onClick={isButton ? onClick : undefined}
      type={isButton ? 'button' : undefined}
      className={cn(
        'flex w-full min-h-[56px] items-center gap-3 px-4 py-3 text-left',
        isButton
          ? 'transition-colors active:bg-muted/60 hover:bg-muted/40'
          : '',
        className,
      )}
    >
      {Icon && (
        <Icon className="h-5 w-5 shrink-0 text-muted-foreground" strokeWidth={1.75} />
      )}
      <div className="min-w-0 flex-1">
        <div className="truncate text-[14px] font-medium leading-tight">{title}</div>
        {subtitle && (
          <div className="mt-0.5 truncate text-[12px] text-muted-foreground">
            {subtitle}
          </div>
        )}
      </div>
      <div className="ml-auto flex shrink-0 items-center gap-1.5 text-muted-foreground">
        {trailing ?? (isButton ? <ChevronRight className="h-4 w-4" /> : null)}
      </div>
    </Element>
  )
}
