import { useState } from 'react'
import { Menu } from 'lucide-react'
import { Link, useLocation, useParams } from 'react-router-dom'

import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { useLastViewedProject } from '@/lib/projectContext'
import { cn } from '@/lib/utils'

import { isNavItemActive, navItems, resolveNavHref } from './nav-items'

export function MobileNav() {
  const [open, setOpen] = useState(false)
  const { projectId: routeProjectId } = useParams<{ projectId: string }>()
  const lastViewedProjectId = useLastViewedProject((s) => s.projectId)
  const { pathname } = useLocation()

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger
        aria-label="Open menu"
        className="md:hidden inline-flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
      >
        <Menu className="h-5 w-5" />
      </SheetTrigger>
      <SheetContent side="left" className="bg-sidebar text-sidebar-foreground p-0 w-[260px] border-r-0">
        <div className="px-5 py-5 border-b border-white/10">
          <div className="text-[15px] font-semibold tracking-tight text-white">Research Assistant</div>
          <div className="mt-0.5 text-[11px] uppercase tracking-wider text-white/50">Manuscripts</div>
        </div>
        <nav className="px-2 py-3">
          {navItems.map((item) => {
            const href = resolveNavHref(item, { routeProjectId, lastViewedProjectId })
            const active = isNavItemActive(item, pathname)
            return (
              <Link
                key={item.slug || 'dashboard'}
                to={href}
                onClick={() => setOpen(false)}
                className={cn(
                  'flex items-center gap-3 h-11 px-3 rounded-md text-[14px] font-medium transition-colors',
                  'text-white/70 hover:text-white hover:bg-white/[0.06]',
                  active && 'text-white bg-white/[0.08]',
                )}
              >
                <item.icon className="h-[16px] w-[16px] shrink-0" />
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>
      </SheetContent>
    </Sheet>
  )
}
