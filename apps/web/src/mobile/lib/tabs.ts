/**
 * Phase M0.5 — bottom-tab definitions consumed by BottomTabs.
 *
 * Five fixed tabs (locked by the build plan). Each tab links to a
 * route under `/m/*` and renders a Lucide icon + a short label.
 * The component layer pairs `Library`/`FileText`/`BarChart3`/
 * `BookOpen`/`Menu` icons with each entry; we keep the icon string
 * here so tests can assert tab identity without dragging lucide-react
 * into the snapshot.
 */
import {
  BarChart3,
  BookOpen,
  FileText,
  Library,
  Menu,
  type LucideIcon,
} from 'lucide-react'

export type MobileTab = {
  /** Stable id used for keys + analytics. */
  id: 'library' | 'manuscripts' | 'stats' | 'learn' | 'more'
  /** Tab label visible under the icon. */
  label: string
  /** Route path the tab navigates to. */
  path: string
  /** Lucide icon component. */
  icon: LucideIcon
  /** ARIA label for the touch target. */
  ariaLabel: string
}

export const MOBILE_TABS: readonly MobileTab[] = [
  {
    id: 'library',
    label: 'Library',
    path: '/m/library',
    icon: Library,
    ariaLabel: 'Open library',
  },
  {
    id: 'manuscripts',
    label: 'Manuscripts',
    path: '/m/manuscripts',
    icon: FileText,
    ariaLabel: 'Open manuscripts',
  },
  {
    id: 'stats',
    label: 'Stats',
    path: '/m/stats',
    icon: BarChart3,
    ariaLabel: 'Open statistics',
  },
  {
    id: 'learn',
    label: 'Learn',
    path: '/m/learn',
    icon: BookOpen,
    ariaLabel: 'Open learn hub',
  },
  {
    id: 'more',
    label: 'More',
    path: '/m/more',
    icon: Menu,
    ariaLabel: 'Open more menu',
  },
] as const
