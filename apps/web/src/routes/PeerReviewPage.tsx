/**
 * Phase 4.6 — AI Peer Review workspace.
 *
 * Two modes share a single page:
 *
 *   Mode 1 (default) — Review the project's current in-app manuscript.
 *   Mode 2          — Review an externally uploaded PDF/DOCX.
 *
 * Layout:
 *   left  = mode picker + history list of past reviews
 *   right = active critique (collapsible cards)
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useMemo, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  peerReviewsApi,
  type PeerReviewRead,
  type PeerReviewRecommendation,
  type PeerReviewSummary,
} from '@/lib/api'
import { useProjectId } from '@/lib/projectContext'

const REC_LABELS: Record<PeerReviewRecommendation, string> = {
  reject: 'Reject',
  major_revision: 'Major Revision',
  minor_revision: 'Minor Revision',
  accept: 'Accept',
}

const REC_BADGE_CLASS: Record<PeerReviewRecommendation, string> = {
  reject: 'bg-red-100 text-red-800 border-red-200',
  major_revision: 'bg-amber-100 text-amber-800 border-amber-200',
  minor_revision: 'bg-blue-100 text-blue-800 border-blue-200',
  accept: 'bg-green-100 text-green-800 border-green-200',
}

const CRITIQUE_SECTIONS: Array<{ key: string; label: string }> = [
  { key: 'strengths', label: 'Strengths' },
  { key: 'major_issues', label: 'Major Issues' },
  { key: 'minor_issues', label: 'Minor Issues' },
  { key: 'methodological_concerns', label: 'Methodological Concerns' },
  { key: 'statistical_concerns', label: 'Statistical Concerns' },
  { key: 'reporting_concerns', label: 'Reporting Concerns' },
  { key: 'presentation_concerns', label: 'Presentation Concerns' },
  { key: 'references_concerns', label: 'References Concerns' },
  { key: 'suggestions_for_improvement', label: 'Suggestions for Improvement' },
]

type Mode = 'manuscript' | 'upload'

export default function PeerReviewPage() {
  const projectId = useProjectId()
  return <PeerReviewInner projectId={projectId} />
}

function PeerReviewInner({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const [mode, setMode] = useState<Mode>('manuscript')
  const [activeId, setActiveId] = useState<string | null>(null)

  const { data: history = [], isLoading: historyLoading } = useQuery({
    queryKey: ['peer-reviews', projectId],
    queryFn: () => peerReviewsApi.list(projectId),
  })

  const active = useMemo(
    () => history.find((h) => h.id === activeId) ?? null,
    [history, activeId],
  )

  const fullActive = useQuery({
    queryKey: ['peer-review', projectId, active?.id],
    queryFn: () =>
      active ? peerReviewsApi.get(projectId, active.id) : Promise.resolve(null),
    enabled: !!active,
  })

  const generateManuscript = useMutation({
    mutationFn: () => peerReviewsApi.generateFromManuscript(projectId),
    onSuccess: (row) => {
      setActiveId(row.id)
      qc.invalidateQueries({ queryKey: ['peer-reviews', projectId] })
      toast.success('Peer review ready')
    },
    onError: (e: Error) => toast.error(e.message || 'Peer review failed'),
  })

  const generateUpload = useMutation({
    mutationFn: (file: File) => peerReviewsApi.generateFromUpload(projectId, file),
    onSuccess: (row) => {
      setActiveId(row.id)
      qc.invalidateQueries({ queryKey: ['peer-reviews', projectId] })
      toast.success('Peer review ready')
    },
    onError: (e: Error) => toast.error(e.message || 'Upload review failed'),
  })

  const deleteReview = useMutation({
    mutationFn: (id: string) => peerReviewsApi.delete(projectId, id),
    onSuccess: () => {
      setActiveId(null)
      qc.invalidateQueries({ queryKey: ['peer-reviews', projectId] })
    },
    onError: (e: Error) => toast.error(e.message || 'Delete failed'),
  })

  const onDrop = useCallback(
    (accepted: File[]) => {
      const file = accepted[0]
      if (!file) return
      generateUpload.mutate(file)
    },
    [generateUpload],
  )
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [
        '.docx',
      ],
    },
  })

  const downloading = useMutation({
    mutationFn: async ({ id, format }: { id: string; format: 'pdf' | 'docx' }) => {
      const blob = await peerReviewsApi.download(projectId, id, format)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `peer-review-${id}.${format}`
      a.click()
      URL.revokeObjectURL(url)
    },
  })

  const busy = generateManuscript.isPending || generateUpload.isPending

  return (
    <div
      className="max-w-screen-2xl mx-auto px-8 py-10 space-y-6"
      data-testid="peer-review-page-shell"
    >
      <header>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Review
        </div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">
          AI Peer Review
        </h1>
        <p className="mt-1 text-[13px] text-muted-foreground">
          Send your manuscript or an external paper through an AI peer
          reviewer and get a structured critique you can act on.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        {/* Left column: mode picker + history */}
        <aside className="space-y-4">
          <div className="rounded-md border bg-card p-3">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-2">
              New review
            </div>
            <div className="flex gap-1 mb-3">
              <button
                type="button"
                onClick={() => setMode('manuscript')}
                className={cn(
                  'flex-1 rounded-md px-3 py-2 text-[12px] font-medium transition-colors',
                  mode === 'manuscript'
                    ? 'bg-foreground text-background'
                    : 'bg-muted text-muted-foreground hover:text-foreground',
                )}
                data-testid="peer-review-mode-manuscript"
              >
                My manuscript
              </button>
              <button
                type="button"
                onClick={() => setMode('upload')}
                className={cn(
                  'flex-1 rounded-md px-3 py-2 text-[12px] font-medium transition-colors',
                  mode === 'upload'
                    ? 'bg-foreground text-background'
                    : 'bg-muted text-muted-foreground hover:text-foreground',
                )}
                data-testid="peer-review-mode-upload"
              >
                Upload paper
              </button>
            </div>

            {mode === 'manuscript' ? (
              <Button
                className="w-full"
                disabled={busy}
                onClick={() => generateManuscript.mutate()}
                data-testid="peer-review-generate-button"
              >
                {generateManuscript.isPending ? 'Reviewing…' : 'Generate review'}
              </Button>
            ) : (
              <div
                {...getRootProps({
                  className: cn(
                    'rounded-md border-2 border-dashed p-4 text-center text-[12px] cursor-pointer transition-colors',
                    isDragActive
                      ? 'border-foreground bg-muted/50'
                      : 'border-muted-foreground/30 hover:border-foreground/60',
                    busy && 'opacity-60 pointer-events-none',
                  ),
                })}
                data-testid="peer-review-dropzone"
              >
                <input {...getInputProps()} />
                {generateUpload.isPending
                  ? 'Reviewing uploaded paper…'
                  : isDragActive
                    ? 'Drop the file here…'
                    : 'Drag a PDF or DOCX here, or click to choose'}
              </div>
            )}
          </div>

          <div className="rounded-md border bg-card">
            <div className="px-3 py-2 border-b">
              <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                History
              </div>
            </div>
            <div className="max-h-[60vh] overflow-y-auto" data-testid="peer-review-history">
              {historyLoading && (
                <div className="px-3 py-6 text-center text-[12px] text-muted-foreground">
                  Loading…
                </div>
              )}
              {!historyLoading && history.length === 0 && (
                <div className="px-3 py-6 text-center text-[12px] text-muted-foreground">
                  No reviews yet
                </div>
              )}
              <ul className="divide-y">
                {history.map((row) => (
                  <li key={row.id}>
                    <button
                      type="button"
                      onClick={() => setActiveId(row.id)}
                      className={cn(
                        'w-full text-left px-3 py-2 hover:bg-muted/40 transition-colors',
                        activeId === row.id && 'bg-muted/60',
                      )}
                      data-testid={`peer-review-history-item-${row.id}`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[12px] font-medium truncate">
                          {row.source_title || '(untitled)'}
                        </span>
                        <RecBadge value={row.recommendation} />
                      </div>
                      <div className="mt-1 text-[10px] text-muted-foreground">
                        {row.source_type === 'manuscript'
                          ? 'In-app manuscript'
                          : 'Uploaded paper'}{' '}
                        · {new Date(row.created_at).toLocaleString()}
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </aside>

        {/* Right column: active critique */}
        <section className="space-y-4">
          {!active && (
            <div className="rounded-md border border-dashed bg-card p-10 text-center text-sm text-muted-foreground">
              Generate a new review or pick one from the history to view it
              here.
            </div>
          )}
          {active && (
            <ActiveCritique
              summary={active}
              full={fullActive.data ?? null}
              busy={fullActive.isLoading}
              onDelete={() => deleteReview.mutate(active.id)}
              onDownload={(format) =>
                downloading.mutate({ id: active.id, format })
              }
            />
          )}
        </section>
      </div>
    </div>
  )
}

function RecBadge({ value }: { value: PeerReviewRecommendation }) {
  return (
    <span
      className={cn(
        'inline-flex shrink-0 items-center rounded-full border px-2 py-[1px] text-[10px] font-medium',
        REC_BADGE_CLASS[value],
      )}
      data-testid={`peer-review-rec-${value}`}
    >
      {REC_LABELS[value]}
    </span>
  )
}

function ActiveCritique({
  summary,
  full,
  busy,
  onDelete,
  onDownload,
}: {
  summary: PeerReviewSummary
  full: PeerReviewRead | null
  busy: boolean
  onDelete: () => void
  onDownload: (format: 'pdf' | 'docx') => void
}) {
  const critique = (full?.critique as Record<string, unknown> | null) ?? null
  const impression =
    typeof critique?.['overall_impression'] === 'string'
      ? (critique['overall_impression'] as string)
      : ''

  return (
    <div className="rounded-md border bg-card">
      <header className="px-4 py-3 border-b flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            {summary.source_type === 'manuscript'
              ? 'In-app manuscript'
              : 'Uploaded paper'}
          </div>
          <div className="text-[14px] font-semibold truncate">
            {summary.source_title || '(untitled)'}
          </div>
          <div className="mt-1 text-[10px] text-muted-foreground">
            {new Date(summary.created_at).toLocaleString()} · model{' '}
            {summary.ai_model}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <RecBadge value={summary.recommendation} />
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onDownload('docx')}
            data-testid="peer-review-export-docx"
          >
            DOCX
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onDownload('pdf')}
            data-testid="peer-review-export-pdf"
          >
            PDF
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onDelete}
            data-testid="peer-review-delete"
          >
            Delete
          </Button>
        </div>
      </header>

      <div className="p-4 space-y-4">
        {busy && (
          <div className="text-[12px] text-muted-foreground">Loading…</div>
        )}
        {!busy && impression && (
          <CritiqueCard label="Overall Impression" defaultOpen>
            <p className="text-[13px] leading-relaxed whitespace-pre-line">
              {impression}
            </p>
          </CritiqueCard>
        )}
        {!busy &&
          critique &&
          CRITIQUE_SECTIONS.map(({ key, label }) => {
            const items = critique[key]
            if (!Array.isArray(items) || items.length === 0) return null
            return (
              <CritiqueCard key={key} label={label}>
                <ul className="list-disc pl-5 space-y-1 text-[13px]">
                  {items.map((it, idx) => (
                    <li key={idx}>{String(it)}</li>
                  ))}
                </ul>
              </CritiqueCard>
            )
          })}
      </div>
    </div>
  )
}

function CritiqueCard({
  label,
  children,
  defaultOpen = true,
}: {
  label: string
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="rounded-md border">
      <button
        type="button"
        onClick={() => setOpen((s) => !s)}
        className="w-full flex items-center justify-between px-3 py-2 text-left bg-muted/30 hover:bg-muted/50 transition-colors"
        data-testid={`peer-review-card-${label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}
      >
        <span className="text-[12px] font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <span className="text-muted-foreground">{open ? '−' : '+'}</span>
      </button>
      {open && <div className="p-3">{children}</div>}
    </div>
  )
}
