/**
 * Phase M0.5 — DeviceRouter.
 *
 * Decides whether to render the existing desktop AppShell or the new
 * MobileShell + mobile route tree. The decision is:
 *
 *   - viewport width < 900px AND
 *   - the user hasn't flipped on "Force desktop layout"
 *
 * Some paths are always desktop-shaped regardless of viewport:
 *
 *   - `/login`, `/signup`, `/welcome`, `/invite/:token` — full-screen
 *     auth pages that look fine at any width and aren't part of
 *     either shell.
 *   - any path under `/m/*` is always the mobile shell (the user
 *     explicitly navigated to a mobile-only URL).
 *
 * The component is intentionally tiny — it just picks which tree to
 * mount. The actual auth gate, layouts, etc. live in the per-shell
 * components so the boundary stays clean.
 */
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useIsMobile } from './lib/viewport'

const ALWAYS_DESKTOP_PATHS = ['/login', '/signup', '/welcome', '/invite/']

function isAlwaysDesktop(pathname: string): boolean {
  return ALWAYS_DESKTOP_PATHS.some((p) => pathname.startsWith(p))
}

function isMobileExplicit(pathname: string): boolean {
  return pathname === '/m' || pathname.startsWith('/m/')
}

export type DeviceRouterProps = {
  /** The desktop tree (existing <AppShell> + child routes). */
  desktop: ReactNode
  /** The mobile tree (a <Routes> with `/m/*` children). */
  mobile: ReactNode
}

export function DeviceRouter({ desktop, mobile }: DeviceRouterProps) {
  const location = useLocation()
  const isMobile = useIsMobile()

  // Explicit `/m/*` URL always renders the mobile shell, even on a
  // wide viewport — this lets desktop users preview the PWA by
  // pasting `/m/library` into the address bar.
  if (isMobileExplicit(location.pathname)) {
    return <>{mobile}</>
  }

  // Auth pages live outside both shells.
  if (isAlwaysDesktop(location.pathname)) {
    return <>{desktop}</>
  }

  // M0.5 — small viewports redirect to `/m/library` so users land on
  // the mobile-first home tab. Preserve the original path as `?next=`
  // for the (future) deep-link recovery.
  if (isMobile) {
    return (
      <Navigate
        to={`/m/library`}
        replace
        state={{ from: location.pathname + location.search }}
      />
    )
  }

  return <>{desktop}</>
}
