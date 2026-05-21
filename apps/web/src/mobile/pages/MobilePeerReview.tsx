/**
 * Phase M1.3 — MobilePeerReview.
 *
 * Two-mode entry point on top of the existing `peerReviewsApi`:
 *
 *   1. "Review my manuscript" — opens a <BottomSheet> project picker;
 *      tapping a project hits `generateFromManuscript`.
 *   2. "Upload an article" — opens a native file picker for PDF/DOCX,
 *      then hits `generateFromUpload`.
 *
 * Below the picker is a history list aggregated across every project
 * the user has access to. Tapping a row navigates to
 * `/m/peer-review/:projectId/:id` which renders the critique sections
 * as a stack of collapsible cards.
 *
 * The aggregation pattern (project list → per-project peer review
 * list) is fine for M1's expected scale: a few dozen projects, each
 * with a handful of reviews. If volume grows we'll add a backend
 * /api/peer-reviews/all endpoint in a later phase.
 */
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { format } from 'date-fns'
import { ChevronRight, FileText, Upload } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import {
  peerReviewsApi,
  projectsApi,
  type PeerReviewRecommendation,
  type PeerReviewSummary,
  type Project,
} from '@/lib/api'
import { cn } from '@/lib/utils'

import { BottomSheet } from '../components/BottomSheet'
import { MobileEmpty } from '../components/MobileEmpty'
import { MobileHeader } from '../components/MobileHeader'

type Mode = 'manuscript' | 'upload'

const RECOMMENDATION_BADGE: Record<
  PeerReviewRecommendation,
  { label: string; className: string }
> = {
  reject: { label: 'Reject', className: 'bg-red-500/15 text-red-700 border-red-500/20' },
  major_revision: {
    label: 'Major revision',
    className: 'bg-amber-500/15 text-amber-700 border-amber-500/20',
  },
  minor_revision: {
    label: 'Minor revision',
    className: 'bg-blue-500/15 text-blue-700 border-blue-500/20',
  },
  accept: {
    label: 'Accept',
    className: 'bg-emerald-500/15 text-emerald-700 border-emerald-500/20',
  },
}

export default function MobilePeerReview() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [picker, setPicker] = useState<Mode | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [uploadProjectId, setUploadProjectId] = useState<string | null>(null)

  const projects = useQuery({
    queryKey: ['projects', 'list'],
    queryFn: () => projectsApi.list(),
    staleTime: 60_000,
  })

  // Per-project peer-review lists, parallelised. We could fetch this
  // lazily once a user opens history, but the page is also the first
  // surface they see — front-loading the query lets the history list
  // render without a spinner in 99% of cases.
  const reviewQueries = useQueries({
    queries: (projects.data ?? []).map((p) => ({
      queryKey: ['peer-reviews', p.id],
      queryFn: () => peerReviewsApi.list(p.id),
      staleTime: 60_000,
    })),
  })

  // Combine into a single descending-by-date list.
  const history = useMemo(() => {
    const all: { project: Project; review: PeerReviewSummary }[] = []
    const list = projects.data ?? []
    list.forEach((p, idx) => {
      const q = reviewQueries[idx]
      if (q?.data) {
        for (const r of q.data) all.push({ project: p, review: r })
      }
    })
    all.sort((a, b) =>
      a.review.created_at < b.review.created_at ? 1 : -1,
    )
    return all
  }, [projects.data, reviewQueries])

  const generateFromManuscript = useMutation({
    mutationFn: async (projectId: string) => {
      const out = await peerReviewsApi.generateFromManuscript(projectId)
      return { projectId, review: out }
    },
    onSuccess: ({ projectId, review }) => {
      qc.invalidateQueries({ queryKey: ['peer-reviews', projectId] })
      toast.success('Peer review generated')
      navigate(`/m/peer-review/${projectId}/${review.id}`)
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to generate review')
    },
  })

  const generateFromUpload = useMutation({
    mutationFn: async (args: { projectId: string; file: File }) => {
      const out = await peerReviewsApi.generateFromUpload(args.projectId, args.file)
      return { projectId: args.projectId, review: out }
    },
    onSuccess: ({ projectId, review }) => {
      qc.invalidateQueries({ queryKey: ['peer-reviews', projectId] })
      toast.success('Peer review generated')
      navigate(`/m/peer-review/${projectId}/${review.id}`)
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to generate review')
    },
  })

  function onPickProject(projectId: string) {
    setPicker(null)
    if (picker === 'manuscript') {
      setBusy(projectId)
      generateFromManuscript.mutate(projectId, { onSettled: () => setBusy(null) })
    } else if (picker === 'upload') {
      setUploadProjectId(projectId)
      // Defer one tick so iOS Safari accepts the click coming from a
      // gesture (the BottomSheet close + file open back-to-back can
      // otherwise be blocked).
      setTimeout(() => fileInputRef.current?.click(), 50)
    }
  }

  function onFileChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file || !uploadProjectId) return
    setBusy(uploadProjectId)
    generateFromUpload.mutate(
      { projectId: uploadProjectId, file },
      { onSettled: () => setBusy(null) },
    )
  }

  return (
    <div className="flex min-h-full flex-col bg-background">
      <MobileHeader title="Review" />

      <div className="space-y-4 px-4 py-4">
        {/* Mode picker — two big tap targets */}
        <div className="grid grid-cols-1 gap-3">
          <ModeCard
            icon={FileText}
            title="Review my manuscript"
            subtitle="Run the AI critic over a project's current manuscript draft."
            disabled={busy !== null}
            onClick={() => setPicker('manuscript')}
            testId="mpeer-mode-manuscript"
          />
          <ModeCard
            icon={Upload}
            title="Upload an article"
            subtitle="Drop a PDF or DOCX from another author and ask for a peer review."
            disabled={busy !== null}
            onClick={() => setPicker('upload')}
            testId="mpeer-mode-upload"
          />
        </div>

        <input
          type="file"
          accept=".pdf,.docx"
          ref={fileInputRef}
          onChange={onFileChosen}
          className="hidden"
          data-testid="mpeer-file-input"
        />

        <section className="space-y-2">
          <div className="px-1 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            History
          </div>

          {history.length === 0 && !projects.isLoading && (
            <MobileEmpty
              icon={FileText}
              title="No reviews yet"
              subtitle="Generate a review from a manuscript or an uploaded paper to see it here."
              testId="mpeer-history-empty"
            />
          )}

          {history.length > 0 && (
            <div
              data-testid="mpeer-history-list"
              className="rounded-xl border border-border bg-card divide-y divide-border"
            >
              {history.map(({ project, review }) => {
                const rec = RECOMMENDATION_BADGE[review.recommendation]
                return (
                  <button
                    key={review.id}
                    type="button"
                    onClick={() => navigate(`/m/peer-review/${project.id}/${review.id}`)}
                    data-testid={`mpeer-history-${review.id}`}
                    className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/40 active:bg-muted/60"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-[14px] font-medium">
                        {review.source_title || 'Untitled'}
                      </div>
                      <div className="mt-0.5 truncate text-[11px] text-muted-foreground">
                        {project.title} ·{' '}
                        {format(new Date(review.created_at), 'd LLL yyyy')}
                      </div>
                    </div>
                    <Badge
                      variant="outline"
                      className={cn('shrink-0 text-[10px]', rec.className)}
                    >
                      {rec.label}
                    </Badge>
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </button>
                )
              })}
            </div>
          )}
        </section>
      </div>

      <BottomSheet
        open={picker !== null}
        onClose={() => setPicker(null)}
        title={picker === 'manuscript' ? 'Choose a project' : 'Choose a project for upload'}
        snapPoints={['60%']}
      >
        {projects.isLoading && (
          <div className="py-6 text-center text-[13px] text-muted-foreground">
            Loading projects…
          </div>
        )}
        {!projects.isLoading && (projects.data?.length ?? 0) === 0 && (
          <div className="py-6 text-center text-[13px] text-muted-foreground">
            No projects found.
          </div>
        )}
        {(projects.data ?? []).map((p) => (
          <button
            key={p.id}
            type="button"
            data-testid={`mpeer-project-${p.id}`}
            onClick={() => onPickProject(p.id)}
            className="flex w-full items-center justify-between border-b border-border last:border-b-0 py-3 text-left"
          >
            <div className="min-w-0">
              <div className="truncate text-[14px] font-medium">{p.title}</div>
              {p.description && (
                <div className="mt-0.5 line-clamp-1 text-[11px] text-muted-foreground">
                  {p.description}
                </div>
              )}
            </div>
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          </button>
        ))}
      </BottomSheet>
    </div>
  )
}

function ModeCard({
  icon: Icon,
  title,
  subtitle,
  onClick,
  disabled,
  testId,
}: {
  icon: typeof FileText
  title: string
  subtitle: string
  onClick: () => void
  disabled?: boolean
  testId: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className={cn(
        'flex w-full items-start gap-3 rounded-xl border border-border bg-card p-4 text-left transition-colors',
        disabled
          ? 'opacity-60'
          : 'hover:border-foreground/20 hover:bg-muted/40 active:bg-muted/60',
      )}
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[15px] font-semibold leading-tight">{title}</div>
        <div className="mt-1 text-[12px] text-muted-foreground">{subtitle}</div>
      </div>
      <ChevronRight className="mt-1 h-4 w-4 text-muted-foreground" />
    </button>
  )
}
