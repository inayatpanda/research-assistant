/**
 * Phase M1.3 — Per-review detail view.
 *
 * Mounted at `/m/peer-review/:projectId/:id`. The critique blob has a
 * known shape (mirrored across PDF / DOCX / manuscript sources) so we
 * render each section as its own collapsible card. The bottom action
 * bar surfaces Export-as-DOCX and Delete.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronDown, Download, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  peerReviewsApi,
  type PeerReviewRecommendation,
} from '@/lib/api'
import { cn } from '@/lib/utils'

import { MobileHeader } from '../components/MobileHeader'

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

const SECTIONS: { key: string; title: string }[] = [
  { key: 'overall_impression', title: 'Overall impression' },
  { key: 'strengths', title: 'Strengths' },
  { key: 'major_issues', title: 'Major issues' },
  { key: 'minor_issues', title: 'Minor issues' },
  { key: 'methodological_concerns', title: 'Methodological concerns' },
  { key: 'statistical_concerns', title: 'Statistical concerns' },
  { key: 'reporting_concerns', title: 'Reporting concerns' },
  { key: 'presentation_concerns', title: 'Presentation' },
  { key: 'references_concerns', title: 'References' },
  { key: 'suggestions_for_improvement', title: 'Suggestions' },
]

export default function MobilePeerReviewDetail() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const params = useParams<{ projectId: string; id: string }>()
  const projectId = params.projectId ?? ''
  const id = params.id ?? ''
  const [open, setOpen] = useState<Record<string, boolean>>({
    overall_impression: true,
    strengths: true,
    major_issues: true,
  })

  const detail = useQuery({
    queryKey: ['peer-review', projectId, id],
    queryFn: () => peerReviewsApi.get(projectId, id),
    enabled: !!projectId && !!id,
    staleTime: 60_000,
  })

  const exportMutation = useMutation({
    mutationFn: async () => {
      const blob = await peerReviewsApi.download(projectId, id, 'docx')
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `peer-review-${id}.docx`
      a.click()
      URL.revokeObjectURL(url)
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : 'Export failed'),
  })

  const deleteMutation = useMutation({
    mutationFn: () => peerReviewsApi.delete(projectId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['peer-reviews', projectId] })
      toast.success('Review deleted')
      navigate('/m/peer-review', { replace: true })
    },
    onError: (err) =>
      toast.error(err instanceof Error ? err.message : 'Delete failed'),
  })

  const review = detail.data
  const critique = (review?.critique ?? {}) as Record<string, unknown>
  const rec = review ? RECOMMENDATION_BADGE[review.recommendation] : null

  return (
    <div className="flex min-h-full flex-col bg-background">
      <MobileHeader
        title={review?.source_title ?? 'Peer review'}
        onBack={() => navigate(-1)}
      />

      {detail.isLoading && (
        <div className="px-4 py-12 text-center text-[13px] text-muted-foreground">
          Loading critique…
        </div>
      )}

      {review && (
        <div data-testid="mpeer-detail-body" className="space-y-3 px-4 py-3 pb-32">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              {rec && (
                <Badge variant="outline" className={cn('text-[11px]', rec.className)}>
                  {rec.label}
                </Badge>
              )}
              <Badge variant="secondary" className="text-[10px] uppercase tracking-wide">
                {review.source_type.replace(/_/g, ' ')}
              </Badge>
              <span className="text-[11px] text-muted-foreground">
                {review.ai_model}
              </span>
            </div>
            <h1 className="text-[18px] font-semibold leading-tight">
              {review.source_title || 'Untitled'}
            </h1>
          </div>

          {SECTIONS.map((s) => (
            <Section
              key={s.key}
              title={s.title}
              expanded={open[s.key] ?? false}
              onToggle={() => setOpen((p) => ({ ...p, [s.key]: !p[s.key] }))}
              content={critique[s.key]}
              testId={`mpeer-section-${s.key}`}
            />
          ))}
        </div>
      )}

      {review && (
        <div
          className={cn(
            'fixed inset-x-0 bottom-[calc(64px+env(safe-area-inset-bottom))] z-20',
            'border-t border-border bg-background/95 backdrop-blur px-4 py-3',
            'flex gap-2',
          )}
        >
          <Button
            variant="default"
            className="flex-1"
            disabled={exportMutation.isPending}
            onClick={() => exportMutation.mutate()}
            data-testid="mpeer-export"
          >
            <Download className="mr-2 h-4 w-4" />
            Export DOCX
          </Button>
          <Button
            variant="destructive"
            className="shrink-0"
            disabled={deleteMutation.isPending}
            onClick={() => {
              if (window.confirm('Delete this peer review?')) {
                deleteMutation.mutate()
              }
            }}
            data-testid="mpeer-delete"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  )
}

function Section({
  title,
  expanded,
  onToggle,
  content,
  testId,
}: {
  title: string
  expanded: boolean
  onToggle: () => void
  content: unknown
  testId: string
}) {
  const items = Array.isArray(content)
    ? (content as unknown[]).filter((x) => typeof x === 'string')
    : null
  const stringContent = typeof content === 'string' ? content : null
  const empty =
    (items && items.length === 0) || (!items && !stringContent) || stringContent === ''

  return (
    <div
      data-testid={testId}
      className="rounded-xl border border-border bg-card overflow-hidden"
    >
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
        aria-expanded={expanded}
      >
        <span className="text-[14px] font-semibold">
          {title}
          {!empty && items && items.length > 0 && (
            <span className="ml-2 text-[11px] font-normal text-muted-foreground">
              ({items.length})
            </span>
          )}
        </span>
        <ChevronDown
          className={cn(
            'h-4 w-4 text-muted-foreground transition-transform',
            expanded ? 'rotate-180' : 'rotate-0',
          )}
        />
      </button>
      {expanded && (
        <div className="border-t border-border px-4 py-3 text-[13px] leading-relaxed">
          {empty && (
            <div className="text-muted-foreground text-[12px] italic">
              No notes in this section.
            </div>
          )}
          {!empty && items && (
            <ul className="list-disc space-y-1.5 pl-5">
              {(items as string[]).map((it, i) => (
                <li key={i}>{it}</li>
              ))}
            </ul>
          )}
          {!empty && !items && stringContent && (
            <p className="whitespace-pre-wrap">{stringContent}</p>
          )}
        </div>
      )}
    </div>
  )
}
