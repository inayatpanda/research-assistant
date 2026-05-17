import { format } from 'date-fns'
import { motion } from 'framer-motion'

import { Badge } from '@/components/ui/badge'
import type { Project } from '@/lib/api'
import { cardEnter } from '@/lib/motion'

export function ProjectCard({ project, index }: { project: Project; index: number }) {
  return (
    <motion.div
      variants={cardEnter(index)}
      initial="initial"
      animate="animate"
      className="group p-5 rounded-lg border border-border bg-white hover:shadow-sm transition-shadow cursor-pointer"
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
    </motion.div>
  )
}
