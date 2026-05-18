import {
  BarChart3,
  ClipboardList,
  FileText,
  Layers,
  Library,
  LayoutDashboard,
  PenLine,
  Send,
  Settings as SettingsIcon,
} from 'lucide-react'
import type { ComponentType } from 'react'

export type NavItem = {
  /** Path slug relative to the project (e.g. `library`). Empty string = root. */
  slug: string
  label: string
  icon: ComponentType<{ className?: string }>
  /** When true the link is global (Dashboard / Settings) and is not
   * scoped to a project; clicking it goes to `/<slug>` regardless of
   * which project the user has open. */
  global?: boolean
}

export const navItems: NavItem[] = [
  { slug: '',           label: 'Dashboard',  icon: LayoutDashboard, global: true },
  { slug: 'library',    label: 'Library',    icon: Library },
  { slug: 'reader',     label: 'Reader',     icon: FileText },
  { slug: 'compile',    label: 'Compile',    icon: Layers },
  { slug: 'manuscript', label: 'Manuscript', icon: PenLine },
  { slug: 'review',     label: 'Review',     icon: ClipboardList },
  { slug: 'statistics', label: 'Statistics', icon: BarChart3 },
  { slug: 'submission', label: 'Submission', icon: Send },
  { slug: 'settings',   label: 'Settings',   icon: SettingsIcon, global: true },
]

/**
 * Resolve the actual href for a nav item given the current routing
 * context. Project-scoped items prefer the routed `:projectId`, then
 * fall back to the last-viewed projectId. If neither is available the
 * link points back to the Dashboard so the user can pick a project.
 */
export function resolveNavHref(
  item: NavItem,
  opts: { routeProjectId?: string; lastViewedProjectId?: string | null },
): string {
  if (item.global) return item.slug === '' ? '/' : `/${item.slug}`
  const id = opts.routeProjectId ?? opts.lastViewedProjectId ?? null
  if (!id) return '/'
  return `/projects/${id}/${item.slug}`
}

/** True when the given URL pathname is "active" for this nav item. */
export function isNavItemActive(item: NavItem, pathname: string): boolean {
  if (item.global) {
    if (item.slug === '') return pathname === '/'
    return pathname === `/${item.slug}` || pathname.startsWith(`/${item.slug}/`)
  }
  // Project-scoped: match any /projects/<id>/<slug>(/...).
  const m = pathname.match(/^\/projects\/[^/]+\/([^/?#]+)/)
  return !!m && m[1] === item.slug
}
