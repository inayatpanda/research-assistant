import { format } from 'date-fns'
import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import type { Project } from '@/lib/api'
import { cardEnter } from '@/lib/motion'
import { useActiveProject } from '@/lib/projectContext'

export function ProjectCard({ project, index }: { project: Project; index: number }) {
  const setActive = useActiveProject((s) => s.set)
  const navigate = useNavigate()

  function open() {
    setActive(project.id)
    navigate('/library')
  }

  return (
    <motion.button
      type="button"
      onClick={open}
      variants={cardEnter(index)}
      initial="initial"
      animate="animate"
      whileHover={{ y: -1 }}
      className="group text-left p-5 rounded-lg border border-border bg-white hover:shadow-sm hover:border-accent/40 transition-all w-full focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2"
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
        Open library
        <ArrowRight className="h-3 w-3" />
      </div>
    </motion.button>
  )
}
