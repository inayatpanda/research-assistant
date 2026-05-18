import { motion } from 'framer-motion'
import { Link, useLocation, useParams } from 'react-router-dom'

import { sidebarSlide } from '@/lib/motion'
import { useLastViewedProject } from '@/lib/projectContext'
import { cn } from '@/lib/utils'

import { isNavItemActive, navItems, resolveNavHref } from './nav-items'

export function Sidebar() {
  const { projectId: routeProjectId } = useParams<{ projectId: string }>()
  const lastViewedProjectId = useLastViewedProject((s) => s.projectId)
  const { pathname } = useLocation()

  return (
    <motion.aside
      variants={sidebarSlide}
      initial="initial"
      animate="animate"
      className="hidden md:flex w-[240px] shrink-0 flex-col bg-sidebar text-sidebar-foreground border-r border-black/20"
    >
      <div className="px-5 py-5 border-b border-white/10">
        <div className="text-[15px] font-semibold tracking-tight">Research Assistant</div>
        <div className="mt-0.5 text-[11px] uppercase tracking-wider text-white/50">Manuscripts</div>
      </div>

      <nav className="flex-1 px-2 py-3">
        {navItems.map((item) => {
          const href = resolveNavHref(item, { routeProjectId, lastViewedProjectId })
          const active = isNavItemActive(item, pathname)
          return (
            <Link
              key={item.slug || 'dashboard'}
              to={href}
              className={cn(
                'group relative flex items-center gap-3 h-10 px-3 rounded-md text-[14px] font-medium transition-colors',
                'text-white/70 hover:text-white hover:bg-white/[0.06]',
                active && 'text-white bg-white/[0.08]',
              )}
            >
              {active && (
                <motion.span
                  layoutId="active-bar"
                  className="absolute left-0 top-1.5 bottom-1.5 w-[2px] rounded-r bg-accent"
                />
              )}
              <item.icon className="h-[16px] w-[16px] shrink-0" />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      <div className="border-t border-white/10 px-4 py-3 text-[11px] text-white/40">
        v0.0.1 · local
      </div>
    </motion.aside>
  )
}
