import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Library as LibraryIcon } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { ArticleFilters } from '@/components/library/ArticleFilters'
import { ArticleListItem } from '@/components/library/ArticleListItem'
import { MetadataConfirmDialog } from '@/components/library/MetadataConfirmDialog'
import { ProjectSelectGate } from '@/components/library/ProjectSelectGate'
import { UploadZone } from '@/components/library/UploadZone'
import { Skeleton } from '@/components/ui/skeleton'
import {
  articlesApi,
  projectsApi,
  type Article,
  type ArticleFilters as Filters,
  type UploadResponse,
} from '@/lib/api'
import { pageEnter } from '@/lib/motion'
import { useActiveProject } from '@/lib/projectContext'

export default function LibraryPage() {
  const projectId = useActiveProject((s) => s.projectId)
  const [filters, setFilters] = useState<Filters>({ sort: 'created_desc' })
  const [editing, setEditing] = useState<Article | null>(null)
  const qc = useQueryClient()

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => (projectId ? projectsApi.get(projectId) : Promise.resolve(null)),
    enabled: !!projectId,
  })

  const { data: articles = [], isLoading } = useQuery({
    queryKey: ['articles', projectId, filters],
    queryFn: () => articlesApi.list(projectId!, filters),
    enabled: !!projectId,
  })

  const del = useMutation({
    mutationFn: (id: string) => articlesApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['articles', projectId] })
      toast.success('Article deleted')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  if (!projectId) return <ProjectSelectGate />

  function onUploaded(response: UploadResponse) {
    // Open metadata confirm for the newly created article so user can review extraction
    setEditing(response.article)
  }

  return (
    <motion.div
      variants={pageEnter}
      initial="initial"
      animate="animate"
      exit="exit"
      className="max-w-6xl mx-auto px-8 py-10 space-y-8"
    >
      <header className="flex items-center justify-between gap-4">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Library · {project?.study_type ?? '—'}
          </div>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight truncate">
            {project?.title ?? 'Loading…'}
          </h1>
          <div className="mt-1 text-[13px] text-muted-foreground">
            {articles.length} article{articles.length === 1 ? '' : 's'}
          </div>
        </div>
      </header>

      <UploadZone projectId={projectId} onUploaded={onUploaded} />

      <section className="space-y-4">
        <ArticleFilters value={filters} onChange={setFilters} />

        {isLoading && (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-[88px] rounded-lg" />
            ))}
          </div>
        )}

        {!isLoading && articles.length === 0 && (
          <div className="rounded-lg border border-dashed border-border bg-white/40 p-12 text-center">
            <LibraryIcon className="h-7 w-7 mx-auto text-muted-foreground" />
            <div className="mt-3 text-[14px] font-medium">No articles yet</div>
            <div className="mt-1 text-[13px] text-muted-foreground">
              Drop a PDF or Word doc above to start your library.
            </div>
          </div>
        )}

        {!isLoading && articles.length > 0 && (
          <div className="space-y-2">
            {articles.map((a, i) => (
              <ArticleListItem
                key={a.id}
                article={a}
                index={i}
                onEdit={(art) => setEditing(art)}
                onDelete={(art) => {
                  if (confirm(`Delete "${art.title}"? The file will also be removed.`)) {
                    del.mutate(art.id)
                  }
                }}
              />
            ))}
          </div>
        )}
      </section>

      <MetadataConfirmDialog
        article={editing}
        open={!!editing}
        onOpenChange={(o) => !o && setEditing(null)}
      />
    </motion.div>
  )
}
