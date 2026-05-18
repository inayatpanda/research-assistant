/**
 * MP12.5 — Topbar project switcher.
 *
 * Lists every project from `projectsApi.list()` and lets the user jump
 * to one (in-tab) or open it in a new tab via the inline ⤴ button.
 * When sitting on `/projects/:projectId/*` the trigger shows that
 * project's title; on the global pages (Dashboard / Settings / Health)
 * it shows a neutral "Pick a project" label.
 */
import { useQuery } from '@tanstack/react-query'
import { Check, ChevronDown, ExternalLink, FolderOpen } from 'lucide-react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { projectsApi } from '@/lib/api'
import { useProject } from '@/lib/projectContext'
import { cn } from '@/lib/utils'

export function ProjectSwitcher() {
  const navigate = useNavigate()
  const { projectId: routeProjectId } = useParams<{ projectId: string }>()
  const ctxProject = useProject()
  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  const triggerLabel =
    ctxProject?.title ??
    projects.find((p) => p.id === routeProjectId)?.title ??
    (routeProjectId ? 'Loading project…' : 'Pick a project')

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          'inline-flex items-center gap-1.5 max-w-[260px] truncate rounded-md',
          'border border-border bg-white px-2.5 py-1 text-[12px] font-medium',
          'hover:border-accent/40 hover:shadow-sm transition-colors',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent',
        )}
        aria-label="Switch project"
      >
        <FolderOpen className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="truncate">{triggerLabel}</span>
        <ChevronDown className="h-3 w-3 text-muted-foreground shrink-0" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[300px]">
        <DropdownMenuItem asChild>
          <Link
            to="/"
            className="text-[12px] font-medium cursor-pointer flex items-center gap-2"
          >
            <FolderOpen className="h-3.5 w-3.5" />
            All projects · Dashboard
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <a
            href="/"
            target="_blank"
            rel="noreferrer"
            className="text-[12px] cursor-pointer flex items-center gap-2"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            Open new project picker in new tab
          </a>
        </DropdownMenuItem>
        {projects.length > 0 && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuLabel className="text-[10px] uppercase tracking-wider text-muted-foreground">
              Projects
            </DropdownMenuLabel>
            {projects.map((p) => {
              const href = `/projects/${p.id}`
              const isActive = p.id === routeProjectId
              return (
                <div
                  key={p.id}
                  className={cn(
                    'group flex items-center gap-1 rounded-sm',
                    isActive && 'bg-muted/50',
                  )}
                >
                  <button
                    type="button"
                    onClick={() => navigate(href)}
                    className="flex-1 min-w-0 flex items-center gap-2 px-2 py-1.5 text-[12px] text-left rounded-sm hover:bg-accent/10"
                  >
                    {isActive ? (
                      <Check className="h-3.5 w-3.5 text-accent shrink-0" />
                    ) : (
                      <span className="w-3.5 shrink-0" />
                    )}
                    <span className="flex-1 min-w-0">
                      <span className="block truncate font-medium">
                        {p.title}
                      </span>
                      <span className="block truncate text-[10px] uppercase tracking-wider text-muted-foreground">
                        {p.study_type}
                      </span>
                    </span>
                  </button>
                  <a
                    href={href}
                    target="_blank"
                    rel="noreferrer"
                    title="Open in new tab"
                    aria-label={`Open ${p.title} in new tab`}
                    className="px-2 py-1.5 text-muted-foreground hover:text-foreground"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </div>
              )
            })}
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
