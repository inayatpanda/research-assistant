import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { ChevronsLeft, ChevronsRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'

import { projectsApi } from '@/lib/api'
import { sidebarSlide } from '@/lib/motion'
import { useLastViewedProject } from '@/lib/projectContext'
import { cn } from '@/lib/utils'

import { isNavItemActive, navItems, resolveNavHref } from './nav-items'

const SIDEBAR_COLLAPSE_KEY = 'sidebar-nav-collapsed'

function readCollapsed(): boolean {
  if (typeof window === 'undefined') return false
  try {
    return window.localStorage.getItem(SIDEBAR_COLLAPSE_KEY) === '1'
  } catch {
    return false
  }
}

function writeCollapsed(v: boolean) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(SIDEBAR_COLLAPSE_KEY, v ? '1' : '0')
  } catch {
    // Ignore quota / disabled-storage errors.
  }
}

export function Sidebar() {
  const { projectId: routeProjectId } = useParams<{ projectId: string }>()
  const storedLastViewedProjectId = useLastViewedProject((s) => s.projectId)
  const clearLastViewed = useLastViewedProject((s) => s.clear)
  const { pathname } = useLocation()
  const [collapsed, setCollapsed] = useState<boolean>(() => readCollapsed())

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev
      writeCollapsed(next)
      return next
    })
  }

  // #N1 — validate the persisted lastViewedProjectId before letting the
  // sidebar route project-scoped nav items to it. If the project has been
  // deleted (or was never created), the stored id leaks "phantom" links
  // that 404 when clicked. We refresh once per session.
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
    staleTime: 1000 * 60 * 5,
    // Don't block sidebar render on the network.
    placeholderData: [],
  })
  const knownProjectIds = (projects ?? []).map((p) => p.id)
  const lastViewedProjectId =
    storedLastViewedProjectId && knownProjectIds.includes(storedLastViewedProjectId)
      ? storedLastViewedProjectId
      : null

  // If the stored id is stale (project deleted), clear it so other surfaces
  // stop linking to it. Only clear once we have a resolved list.
  useEffect(() => {
    if (
      projects &&
      projects.length > 0 &&
      storedLastViewedProjectId &&
      !projects.some((p) => p.id === storedLastViewedProjectId)
    ) {
      clearLastViewed()
    }
  }, [projects, storedLastViewedProjectId, clearLastViewed])

  return (
    <motion.aside
      variants={sidebarSlide}
      initial="initial"
      animate="animate"
      data-testid="sidebar"
      data-collapsed={collapsed ? 'true' : 'false'}
      className={cn(
        'hidden md:flex shrink-0 flex-col bg-sidebar text-sidebar-foreground border-r border-black/20 transition-[width] duration-200',
        collapsed ? 'w-[56px]' : 'w-[240px]',
      )}
    >
      <div
        className={cn(
          'border-b border-white/10 flex items-center',
          collapsed ? 'justify-center py-4 px-2' : 'justify-between px-5 py-5',
        )}
      >
        {!collapsed && (
          <div className="min-w-0">
            <div className="text-[15px] font-semibold tracking-tight truncate">
              Research Assistant
            </div>
            <div className="mt-0.5 text-[11px] uppercase tracking-wider text-white/50">
              Manuscripts
            </div>
          </div>
        )}
        <button
          type="button"
          onClick={toggleCollapsed}
          data-testid="sidebar-collapse-toggle"
          aria-label={collapsed ? 'Expand nav' : 'Collapse nav'}
          aria-pressed={collapsed}
          className="rounded-md p-1.5 text-white/60 hover:text-white hover:bg-white/[0.08] transition-colors"
        >
          {collapsed ? (
            <ChevronsRight className="h-4 w-4" />
          ) : (
            <ChevronsLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      <nav className="flex-1 px-2 py-3">
        {navItems.map((item) => {
          const href = resolveNavHref(item, { routeProjectId, lastViewedProjectId })
          const active = isNavItemActive(item, pathname)
          return (
            <Link
              key={item.slug || 'dashboard'}
              to={href}
              title={collapsed ? item.label : undefined}
              aria-label={collapsed ? item.label : undefined}
              className={cn(
                'group relative flex items-center h-10 rounded-md text-[14px] font-medium transition-colors',
                'text-white/70 hover:text-white hover:bg-white/[0.06]',
                active && 'text-white bg-white/[0.08]',
                collapsed ? 'justify-center px-0' : 'gap-3 px-3',
              )}
            >
              {active && (
                <motion.span
                  layoutId="active-bar"
                  className="absolute left-0 top-1.5 bottom-1.5 w-[2px] rounded-r bg-accent"
                />
              )}
              <item.icon className="h-[16px] w-[16px] shrink-0" />
              {!collapsed && <span>{item.label}</span>}
            </Link>
          )
        })}
      </nav>

      {!collapsed && (
        <div className="border-t border-white/10 px-4 py-3 text-[11px] text-white/40">
          v0.0.1 · local
        </div>
      )}
    </motion.aside>
  )
}
