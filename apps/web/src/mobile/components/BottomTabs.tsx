/**
 * Phase M0.5 — fixed bottom tab bar for the mobile shell.
 *
 * Five tabs (Library / Manuscripts / Stats / Learn / More). The bar is
 * 64pt tall + ``env(safe-area-inset-bottom)`` so an iPhone with a home
 * indicator never overlaps the tap targets.
 *
 * Each tab target is ≥ 44×44pt (HIG minimum). The active tab gets a
 * filled icon (lucide-react's ``fill="currentColor"``), accent text,
 * and a small underline indicator at the top of the touch area.
 */
import { NavLink } from 'react-router-dom'

import { cn } from '@/lib/utils'

import { MOBILE_TABS, type MobileTab } from '../lib/tabs'

export function BottomTabs() {
  return (
    <nav
      aria-label="Primary"
      data-testid="mobile-bottom-tabs"
      className={cn(
        'fixed inset-x-0 bottom-0 z-30 w-full',
        'border-t border-border bg-background/95 backdrop-blur',
        // Safe-area inset bottom keeps the tab labels above the iPhone
        // home indicator on devices with a notch.
        'pb-[env(safe-area-inset-bottom)]',
      )}
    >
      <ul className="flex h-16 w-full items-stretch justify-around">
        {MOBILE_TABS.map((tab) => (
          <TabItem key={tab.id} tab={tab} />
        ))}
      </ul>
    </nav>
  )
}

function TabItem({ tab }: { tab: MobileTab }) {
  const Icon = tab.icon
  return (
    <li className="flex flex-1 items-stretch">
      <NavLink
        to={tab.path}
        aria-label={tab.ariaLabel}
        data-tab-id={tab.id}
        className={({ isActive }) =>
          cn(
            'group relative flex flex-1 flex-col items-center justify-center',
            'min-h-[44px] gap-0.5 text-[11px] font-medium',
            'transition-colors',
            isActive
              ? 'text-primary'
              : 'text-muted-foreground hover:text-foreground',
          )
        }
      >
        {({ isActive }) => (
          <>
            {isActive ? (
              <span
                aria-hidden="true"
                data-testid={`tab-indicator-${tab.id}`}
                className="absolute top-0 h-0.5 w-8 rounded-full bg-primary"
              />
            ) : null}
            <Icon
              className="h-5 w-5"
              fill={isActive ? 'currentColor' : 'none'}
              strokeWidth={isActive ? 1.75 : 2}
            />
            <span>{tab.label}</span>
          </>
        )}
      </NavLink>
    </li>
  )
}
