import { format } from 'date-fns'
import { motion } from 'framer-motion'
import { ArrowRight, ExternalLink } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import type { Project } from '@/lib/api'
import { cardEnter } from '@/lib/motion'

export function ProjectCard({ project, index }: { project: Project; index: number }) {
  const navigate = useNavigate()

  function open() {
    // MP12.5 — open the project home page instead of mutating a global
    // "active project" Zustand store. URL is now the source of truth.
    navigate(`/projects/${project.id}`)
  }

  const newTabHref = `/projects/${project.id}`

  return (
    <motion.div
      variants={cardEnter(index)}
      initial="initial"
      animate="animate"
      whileHover={{ y: -1 }}
      className="group relative p-5 rounded-lg border border-border bg-white hover:shadow-sm hover:border-accent/40 transition-all"
    >
      <button
        type="button"
        onClick={open}
        className="text-left w-full focus:outline-none"
      >
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-[15px] font-semibold tracking-tight leading-tight line-clamp-2">
            {project.title}
          </h3>
          <Badge
            variant="secondary"
            className="shrink-0 text-[10px] uppercase tracking-wider font-medium"
          >
            {project.study_type}
          </Badge>
        </div>
        <div className="mt-4 flex items-center justify-between text-[12px] text-muted-foreground">
          <span>
            {project.citation_style.toUpperCase()} · {project.ai_provider}
          </span>
          <span>{format(new Date(project.created_at), 'MMM d, yyyy')}</span>
        </div>
        <div className="mt-3 flex items-center gap-1 text-[12px] text-accent opacity-0 group-hover:opacity-100 transition-opacity">
          Open project
          <ArrowRight className="h-3 w-3" />
        </div>
      </button>
      <a
        href={newTabHref}
        target="_blank"
        rel="noreferrer"
        title="Open in new tab"
        aria-label={`Open ${project.title} in new tab`}
        onClick={(e) => e.stopPropagation()}
        className="absolute top-2 right-2 p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60 opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <ExternalLink className="h-3.5 w-3.5" />
      </a>
    </motion.div>
  )
}
