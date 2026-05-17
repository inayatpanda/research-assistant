import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FolderOpen, FolderPlus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { projectsApi } from '@/lib/api'
import { pageEnter } from '@/lib/motion'
import { useActiveProject } from '@/lib/projectContext'

export function ProjectSelectGate() {
  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  })
  const setActive = useActiveProject((s) => s.set)
  const navigate = useNavigate()

  return (
    <motion.div
      variants={pageEnter}
      initial="initial"
      animate="animate"
      className="max-w-2xl mx-auto px-8 py-16 text-center"
    >
      <FolderOpen className="h-8 w-8 mx-auto text-muted-foreground" />
      <h2 className="mt-4 text-[20px] font-semibold tracking-tight">Pick a project first</h2>
      <p className="mt-2 text-[14px] text-muted-foreground">
        The library shows articles inside the active project. Open one or create a new project.
      </p>
      {!isLoading && projects.length > 0 && (
        <div className="mt-6 space-y-2 text-left">
          {projects.map((p) => (
            <button
              key={p.id}
              onClick={() => setActive(p.id)}
              className="w-full text-left p-4 rounded-md border border-border bg-white hover:border-accent/40 hover:shadow-sm transition-all"
            >
              <div className="font-medium text-[14px]">{p.title}</div>
              <div className="text-[12px] text-muted-foreground">{p.study_type}</div>
            </button>
          ))}
        </div>
      )}
      <Button onClick={() => navigate('/')} className="mt-6 bg-accent hover:bg-accent-hover text-white">
        <FolderPlus className="h-4 w-4 mr-1.5" />
        Go to Dashboard
      </Button>
    </motion.div>
  )
}
