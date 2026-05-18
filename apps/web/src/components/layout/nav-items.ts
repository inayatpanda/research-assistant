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
  to: string
  label: string
  icon: ComponentType<{ className?: string }>
}

export const navItems: NavItem[] = [
  { to: '/',           label: 'Dashboard',  icon: LayoutDashboard },
  { to: '/library',    label: 'Library',    icon: Library },
  { to: '/reader',     label: 'Reader',     icon: FileText },
  { to: '/compile',    label: 'Compile',    icon: Layers },
  { to: '/manuscript', label: 'Manuscript', icon: PenLine },
  { to: '/review',     label: 'Review',     icon: ClipboardList },
  { to: '/statistics', label: 'Statistics', icon: BarChart3 },
  { to: '/submission', label: 'Submission', icon: Send },
  { to: '/settings',   label: 'Settings',   icon: SettingsIcon },
]
