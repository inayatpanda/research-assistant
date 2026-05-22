import {
  BarChart3,
  BookOpen,
  CheckSquare,
  ClipboardList,
  Coins,
  FileText,
  Layers,
  Library,
  LayoutDashboard,
  MessageSquareWarning,
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
  { slug: 'manuscript',  label: 'Manuscript',         icon: PenLine },
  // Fix-E2E/3 — was bare "Review" (was actually Peer Review). Rename to
  // disambiguate from "Systematic Review" on the same sidebar.
  { slug: 'peer-review', label: 'Peer Review',        icon: MessageSquareWarning },
  { slug: 'systematic-review', label: 'Systematic Review', icon: ClipboardList },
  { slug: 'statistics', label: 'Statistics', icon: BarChart3 },
  { slug: 'economics',  label: 'Economics',  icon: Coins },
  { slug: 'checklists', label: 'Checklists', icon: CheckSquare },
  { slug: 'submission', label: 'Submission', icon: Send },
  // Fix-E2E/LOW — surface a direct entry to the Learn hub; previously
  // reachable only via search-bar/tooltips.
  { slug: 'learn',      label: 'Learn',      icon: BookOpen },
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

/**
 * Fix-E2E/6 — true when a nav item is project-scoped but no project is
 * resolvable. Callers render the item greyed out + non-clickable so the
 * link doesn't silently collapse back to Dashboard.
 */
export function isNavItemDisabled(
  item: NavItem,
  opts: { routeProjectId?: string; lastViewedProjectId?: string | null },
): boolean {
  if (item.global) return false
  const id = opts.routeProjectId ?? opts.lastViewedProjectId ?? null
  return !id
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
