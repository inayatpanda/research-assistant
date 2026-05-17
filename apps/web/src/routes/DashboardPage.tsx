import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FolderOpen } from 'lucide-react'

import { CreateProjectDialog } from '@/components/projects/CreateProjectDialog'
import { ProjectCard } from '@/components/projects/ProjectCard'
import { Skeleton } from '@/components/ui/skeleton'
import { projectsApi } from '@/lib/api'
import { pageEnter } from '@/lib/motion'

export default function DashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })

  return (
    <motion.div
      variants={pageEnter}
      initial="initial"
      animate="animate"
      exit="exit"
      className="max-w-6xl mx-auto px-8 py-10"
    >
      <div className="flex items-center justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Dashboard
          </div>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Your projects</h1>
        </div>
        <CreateProjectDialog />
      </div>

      <div className="mt-8">
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-[112px] rounded-lg" />
            ))}
          </div>
        )}
        {isError && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-6 text-[13px] text-destructive">
            Couldn't reach the API. Make sure the backend is running on :8787 (`npm run dev`).
          </div>
        )}
        {data && data.length === 0 && (
          <div className="mt-2 rounded-lg border border-dashed border-border bg-white/40 p-12 text-center">
            <FolderOpen className="h-7 w-7 mx-auto text-muted-foreground" />
            <div className="mt-3 text-[14px] font-medium">No projects yet</div>
            <div className="mt-1 text-[13px] text-muted-foreground">Create one to get started.</div>
          </div>
        )}
        {data && data.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {data.map((p, i) => (
              <ProjectCard key={p.id} project={p} index={i} />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}
