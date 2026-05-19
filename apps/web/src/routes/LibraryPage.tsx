import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Library as LibraryIcon } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { AddByDoiInline } from '@/components/library/AddByDoiInline'
import { ArticleFilters } from '@/components/library/ArticleFilters'
import { ArticleListItem } from '@/components/library/ArticleListItem'
import { DuplicatesPanel } from '@/components/library/DuplicatesPanel'
import { ImportPreviewDialog } from '@/components/library/ImportPreviewDialog'
import { MetadataConfirmDialog } from '@/components/library/MetadataConfirmDialog'
import { PubMedSearchDialog } from '@/components/library/PubMedSearchDialog'
import { RisBibtexDropzone } from '@/components/library/RisBibtexDropzone'
import { UploadZone } from '@/components/library/UploadZone'
import { Skeleton } from '@/components/ui/skeleton'
import {
  articlesApi,
  projectsApi,
  type Article,
  type ArticleFilters as Filters,
  type ArticleMetadata,
  type UploadResponse,
} from '@/lib/api'
import { pageEnter } from '@/lib/motion'
import { useProjectId } from '@/lib/projectContext'

export default function LibraryPage() {
  const projectId = useProjectId()
  const [filters, setFilters] = useState<Filters>({ sort: 'created_desc' })
  // Articles waiting to be confirmed sit in a FIFO queue. We only show the
  // dialog for the head of the queue so multi-file uploads can't stack
  // dialogs invisibly on top of each other (#L2). Manual edits (from the
  // "Edit" row button) jump to the head so users see their click react.
  const [confirmQueue, setConfirmQueue] = useState<Article[]>([])
  const editing = confirmQueue[0] ?? null
  const [doiPreview, setDoiPreview] = useState<ArticleMetadata | null>(null)
  const qc = useQueryClient()

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
  })

  const { data: articles = [], isLoading } = useQuery({
    queryKey: ['articles', projectId, filters],
    queryFn: () => articlesApi.list(projectId, filters),
  })

  const del = useMutation({
    mutationFn: (id: string) => articlesApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['articles', projectId] })
      toast.success('Article deleted')
    },
    onError: (e: Error) => toast.error(e.message),
  })

  function onUploaded(response: UploadResponse) {
    // Open metadata confirm for the newly created article so user can review
    // extraction. Append to the queue rather than replacing — when several
    // PDFs are uploaded back-to-back each one gets its own dialog turn (#L2).
    setConfirmQueue((q) => [...q, response.article])
  }

  function openEditDialog(article: Article) {
    // Jump manual edits to the front of the queue so the user immediately
    // sees the dialog for the row they just clicked.
    setConfirmQueue((q) => [article, ...q.filter((a) => a.id !== article.id)])
  }

  function advanceQueue() {
    setConfirmQueue((q) => q.slice(1))
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

      <div className="grid gap-3 md:grid-cols-3">
        <AddByDoiInline
          projectId={projectId}
          onResult={(meta) => setDoiPreview(meta)}
        />
        <div className="rounded-lg border border-border bg-white/40 p-4 flex items-center justify-between gap-3">
          <div>
            <div className="text-[12px] font-medium">Search PubMed</div>
            <div className="text-[11px] text-muted-foreground">
              NCBI E-utilities · preview before import
            </div>
          </div>
          <PubMedSearchDialog projectId={projectId} />
        </div>
        <RisBibtexDropzone projectId={projectId} />
      </div>

      <UploadZone projectId={projectId} onUploaded={onUploaded} />

      <DuplicatesPanel projectId={projectId} />

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
                onEdit={openEditDialog}
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
        onOpenChange={(o) => {
          if (!o) advanceQueue()
        }}
      />

      {doiPreview && (
        <ImportPreviewDialog
          projectId={projectId}
          open={!!doiPreview}
          items={[doiPreview]}
          onOpenChange={(o) => {
            if (!o) setDoiPreview(null)
          }}
        />
      )}
    </motion.div>
  )
}
