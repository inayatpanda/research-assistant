/**
 * Phase M5.3 — Mobile Submission mini-app.
 *
 * Lives at ``/m/submission``. Three cards plus a download bar:
 *   - Cover letter card     (read-only preview, edit in bottom sheet, AI draft)
 *   - Response to reviewers (list of past responses, edit/create in sheet,
 *                            AI generate by pasting raw comments)
 *   - Pre-submission check  (auto-checks frontmatter / 6 sections / figures /
 *                            references / cover letter — green tick or amber
 *                            warning per row)
 *
 * Bottom action: "Download submission package" — calls the existing
 * /export/submission-package zip endpoint via exportApi.
 *
 * Project picker chip mirrors MobileStatsUpload.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Download,
  FileText,
  Loader2,
  MessageSquare,
  Pencil,
  Sparkles,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import {
  articlesApi,
  bibliographyApi,
  coverLetterApi,
  exportApi,
  figuresApi,
  frontmatterApi,
  manuscriptApi,
  projectsApi,
  reviewerResponseApi,
  type CoverLetterRead,
  type ManuscriptSectionName,
  type ReviewerResponseRead,
} from '@/lib/api'
import { useLastViewedProject } from '@/lib/projectContext'
import { cn } from '@/lib/utils'

import { BottomSheet } from '../components/BottomSheet'

const SIX_SECTIONS: ManuscriptSectionName[] = [
  'Abstract',
  'Introduction',
  'Methodology',
  'Results',
  'Discussion',
  'Conclusion',
]

function htmlToPlain(html: string): string {
  return html
    .replace(/<\/(p|div|li|h[1-6])>/gi, '\n')
    .replace(/<br\s*\/?\s*>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

export default function MobileSubmission() {
  const lastProjectId = useLastViewedProject((s) => s.projectId)
  const setLastProject = useLastViewedProject((s) => s.set)
  const [picker, setPicker] = useState(false)

  const projects = useQuery({
    queryKey: ['projects', 'list'],
    queryFn: () => projectsApi.list(),
    staleTime: 60_000,
  })

  const activeProjectId = useMemo(() => {
    const list = projects.data ?? []
    if (list.length === 0) return null
    const valid = lastProjectId && list.some((p) => p.id === lastProjectId)
    return valid ? lastProjectId : list[0]?.id ?? null
  }, [projects.data, lastProjectId])

  const activeProject = useMemo(
    () => projects.data?.find((p) => p.id === activeProjectId) ?? null,
    [projects.data, activeProjectId],
  )

  function onPickProject(pid: string) {
    setLastProject(pid)
    setPicker(false)
  }

  const downloadPackage = useMutation({
    mutationFn: async () => {
      if (!activeProjectId) throw new Error('No project selected')
      return exportApi.downloadSubmissionPackage(activeProjectId)
    },
    onSuccess: (filename) => {
      toast.success(`Downloaded ${filename}`)
    },
    onError: (err) => {
      toast.error(
        err instanceof Error ? err.message : 'Failed to download package',
      )
    },
  })

  return (
    <div className="flex min-h-full flex-col bg-background pb-24">
      <div className="px-4 pt-4 pb-1">
        <h2 className="text-[20px] font-semibold tracking-tight">Submission</h2>
      </div>

      {/* Project picker chip */}
      <div className="flex items-center justify-between gap-2 px-4 pt-1 pb-3">
        <button
          type="button"
          onClick={() => setPicker(true)}
          data-testid="msubmission-project-trigger"
          className="flex min-w-0 items-center gap-1 text-left"
        >
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Project
            </div>
            <div className="flex min-w-0 items-center gap-1">
              <h2 className="truncate text-[16px] font-semibold tracking-tight">
                {activeProject?.title ?? 'No project'}
              </h2>
              <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
            </div>
          </div>
        </button>
      </div>

      {activeProjectId && (
        <div className="space-y-3 px-3">
          <CoverLetterCard projectId={activeProjectId} />
          <ReviewerResponseCard projectId={activeProjectId} />
          <PreSubmissionCheckCard projectId={activeProjectId} />
        </div>
      )}

      {/* Bottom action bar */}
      <div className="fixed bottom-[calc(64px+env(safe-area-inset-bottom))] inset-x-0 z-10 border-t border-border bg-background/95 backdrop-blur px-3 py-2">
        <button
          type="button"
          data-testid="msubmission-download"
          onClick={() => downloadPackage.mutate()}
          disabled={!activeProjectId || downloadPackage.isPending}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-3 py-2.5 text-[13px] font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
        >
          {downloadPackage.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          Download submission package
        </button>
      </div>

      {/* Project picker sheet */}
      <BottomSheet
        open={picker}
        onClose={() => setPicker(false)}
        title="Choose a project"
        snapPoints={['60%']}
      >
        {(projects.data ?? []).length === 0 && (
          <div className="py-6 text-center text-[13px] text-muted-foreground">
            No projects found. Create one on the desktop app first.
          </div>
        )}
        {(projects.data ?? []).map((p) => (
          <button
            key={p.id}
            type="button"
            data-testid={`msubmission-project-${p.id}`}
            onClick={() => onPickProject(p.id)}
            className={cn(
              'flex w-full items-center justify-between border-b border-border last:border-b-0 py-3 text-left',
              p.id === activeProjectId && 'font-semibold',
            )}
          >
            <div className="min-w-0">
              <div className="truncate text-[14px]">{p.title}</div>
              <div className="mt-0.5 truncate text-[11px] text-muted-foreground">
                {p.study_type}
              </div>
            </div>
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          </button>
        ))}
      </BottomSheet>
    </div>
  )
}

// ── Cover letter card ────────────────────────────────────────────────────

function CoverLetterCard({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const [editOpen, setEditOpen] = useState(false)
  const [draft, setDraft] = useState('')

  const cover = useQuery({
    queryKey: ['msubmission', 'cover', projectId],
    queryFn: () => coverLetterApi.get(projectId),
    staleTime: 30_000,
  })

  const save = useMutation({
    mutationFn: async (body_html: string) =>
      coverLetterApi.update(projectId, { body_html }),
    onSuccess: (row) => {
      qc.setQueryData(['msubmission', 'cover', projectId], row)
      toast.success('Cover letter saved')
      setEditOpen(false)
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Save failed')
    },
  })

  const aiDraft = useMutation({
    mutationFn: async () => coverLetterApi.draft(projectId),
    onSuccess: (row: CoverLetterRead) => {
      qc.setQueryData(['msubmission', 'cover', projectId], row)
      setDraft(htmlToPlain(row.body_html))
      toast.success('AI drafted a cover letter')
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'AI draft failed')
    },
  })

  function openEdit() {
    setDraft(htmlToPlain(cover.data?.body_html ?? ''))
    setEditOpen(true)
  }

  const preview = htmlToPlain(cover.data?.body_html ?? '')

  return (
    <section
      data-testid="msubmission-cover-card"
      className="rounded-2xl border border-border bg-card p-4 shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            <span className="text-[15px] font-semibold tracking-tight">
              Cover letter
            </span>
          </div>
          {cover.data?.target_journal && (
            <div className="mt-0.5 text-[11px] text-muted-foreground">
              Target: {cover.data.target_journal}
            </div>
          )}
        </div>
        <button
          type="button"
          aria-label="Edit cover letter"
          data-testid="msubmission-cover-edit"
          onClick={openEdit}
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <Pencil className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-3 max-h-32 overflow-hidden rounded-md border border-border bg-muted/30 p-3 text-[12px] text-muted-foreground whitespace-pre-wrap">
        {preview || 'No cover letter yet — tap edit to draft one.'}
      </div>

      <BottomSheet
        open={editOpen}
        onClose={() => setEditOpen(false)}
        title="Edit cover letter"
        snapPoints={['90%']}
      >
        <div className="flex h-full flex-col gap-3">
          <textarea
            data-testid="msubmission-cover-textarea"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={12}
            className="flex-1 w-full rounded-md border border-border bg-background p-3 text-[14px] focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
          <div className="flex items-center gap-2">
            <button
              type="button"
              data-testid="msubmission-cover-ai"
              onClick={() => aiDraft.mutate()}
              disabled={aiDraft.isPending}
              className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-md border border-border bg-card text-[13px] font-medium hover:bg-muted disabled:opacity-60"
            >
              {aiDraft.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              AI draft
            </button>
            <button
              type="button"
              data-testid="msubmission-cover-save"
              onClick={() => save.mutate(draft)}
              disabled={save.isPending}
              className="inline-flex h-10 flex-1 items-center justify-center rounded-md bg-primary px-3 text-[13px] font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
            >
              {save.isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </div>
      </BottomSheet>
    </section>
  )
}

// ── Reviewer response card ──────────────────────────────────────────────

function ReviewerResponseCard({ projectId }: { projectId: string }) {
  const qc = useQueryClient()
  const [editOpen, setEditOpen] = useState(false)
  const [reviewerLabel, setReviewerLabel] = useState('Reviewer 1')
  const [rawComments, setRawComments] = useState('')

  const responses = useQuery({
    queryKey: ['msubmission', 'reviewer-responses', projectId],
    queryFn: () => reviewerResponseApi.list(projectId),
    staleTime: 30_000,
  })

  const generate = useMutation({
    mutationFn: async () =>
      reviewerResponseApi.create(projectId, {
        reviewer_label: reviewerLabel || 'Reviewer 1',
        raw_comments: rawComments,
      }),
    onSuccess: (row: ReviewerResponseRead) => {
      qc.invalidateQueries({
        queryKey: ['msubmission', 'reviewer-responses', projectId],
      })
      toast.success(`Drafted ${row.reviewer_label}`)
      setRawComments('')
      setEditOpen(false)
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'AI draft failed')
    },
  })

  return (
    <section
      data-testid="msubmission-reviewer-card"
      className="rounded-2xl border border-border bg-card p-4 shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-4 w-4 text-muted-foreground" />
            <span className="text-[15px] font-semibold tracking-tight">
              Response to reviewers
            </span>
          </div>
          <div className="mt-0.5 text-[11px] text-muted-foreground">
            {(responses.data ?? []).length} response
            {(responses.data ?? []).length === 1 ? '' : 's'} drafted
          </div>
        </div>
        <button
          type="button"
          aria-label="Add reviewer response"
          data-testid="msubmission-reviewer-edit"
          onClick={() => setEditOpen(true)}
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <Pencil className="h-4 w-4" />
        </button>
      </div>

      <div
        data-testid="msubmission-reviewer-list"
        className="mt-3 space-y-2"
      >
        {(responses.data ?? []).map((r) => (
          <ResponseRow key={r.id} resp={r} />
        ))}
        {responses.data && responses.data.length === 0 && (
          <div className="rounded-md border border-border bg-muted/30 p-3 text-[12px] text-muted-foreground">
            No reviewer responses yet — tap the pencil to paste raw
            comments and let the AI draft replies.
          </div>
        )}
      </div>

      <BottomSheet
        open={editOpen}
        onClose={() => setEditOpen(false)}
        title="Draft reviewer response"
        snapPoints={['85%']}
      >
        <div className="space-y-3 text-[13px]">
          <label className="block">
            <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
              Reviewer label
            </span>
            <input
              type="text"
              data-testid="msubmission-reviewer-label"
              value={reviewerLabel}
              onChange={(e) => setReviewerLabel(e.target.value)}
              className="mt-1 h-10 w-full rounded-md border border-border bg-background px-3 text-[14px] focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
          </label>
          <label className="block">
            <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
              Raw comments (paste from the journal portal)
            </span>
            <textarea
              data-testid="msubmission-reviewer-textarea"
              value={rawComments}
              onChange={(e) => setRawComments(e.target.value)}
              rows={10}
              className="mt-1 w-full rounded-md border border-border bg-background p-2 text-[14px] focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
          </label>
          <button
            type="button"
            data-testid="msubmission-reviewer-ai"
            onClick={() => generate.mutate()}
            disabled={!rawComments.trim() || generate.isPending}
            className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-primary px-3 text-[13px] font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-60"
          >
            {generate.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            AI draft replies
          </button>
        </div>
      </BottomSheet>
    </section>
  )
}

function ResponseRow({ resp }: { resp: ReviewerResponseRead }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div
      data-testid={`msubmission-reviewer-row-${resp.id}`}
      className="rounded-md border border-border bg-muted/30 p-2 text-[12px]"
    >
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center justify-between gap-2 text-left"
      >
        <span className="font-medium">{resp.reviewer_label}</span>
        <Badge variant="secondary" className="text-[10px]">
          {resp.comments.length} comment
          {resp.comments.length === 1 ? '' : 's'}
        </Badge>
      </button>
      {expanded && (
        <ul
          data-testid={`msubmission-reviewer-comments-${resp.id}`}
          className="mt-2 space-y-2"
        >
          {resp.comments.map((c, i) => (
            <li
              key={i}
              className="rounded-md border border-border bg-background p-2"
            >
              <div className="text-muted-foreground">{c.comment_text}</div>
              <div
                className="mt-1 whitespace-pre-wrap"
                dangerouslySetInnerHTML={{ __html: c.response_html }}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// ── Pre-submission auto-check card ──────────────────────────────────────

type CheckRow = {
  key: string
  label: string
  ok: boolean
  detail: string
}

function PreSubmissionCheckCard({ projectId }: { projectId: string }) {
  const checks = useQuery({
    queryKey: ['msubmission', 'pre-check', projectId],
    queryFn: async (): Promise<CheckRow[]> => {
      // Fan-out across the relevant resources and synthesise a row per
      // check. Errors per-query degrade gracefully to "ok: false".
      const settled = await Promise.allSettled([
        frontmatterApi.frontmatter.get(projectId),
        Promise.all(
          SIX_SECTIONS.map((s) =>
            manuscriptApi.getSection(projectId, s).catch(() => null),
          ),
        ),
        figuresApi.list(projectId),
        articlesApi.list(projectId),
        coverLetterApi.get(projectId),
        bibliographyApi.get(projectId),
      ])

      const out: CheckRow[] = []

      // 1. Frontmatter — at least funding/ethics/conflicts populated.
      const fm = settled[0]
      if (fm.status === 'fulfilled') {
        const f = fm.value
        const ok = Boolean(
          f &&
            ((f.funding_statement && f.funding_statement.trim()) ||
              (f.funders && f.funders.length > 0) ||
              (f.ethics_irb && f.ethics_irb.trim()) ||
              (f.conflicts_statement && f.conflicts_statement.trim())),
        )
        out.push({
          key: 'frontmatter',
          label: 'Frontmatter populated',
          ok,
          detail: ok
            ? 'Funding / ethics / conflicts fields are set.'
            : 'Set funding, ethics or conflicts statements in Frontmatter.',
        })
      } else {
        out.push({
          key: 'frontmatter',
          label: 'Frontmatter populated',
          ok: false,
          detail: 'Could not load frontmatter.',
        })
      }

      // 2. All 6 sections have content.
      const secs = settled[1]
      if (secs.status === 'fulfilled') {
        const list = secs.value
        const missing = SIX_SECTIONS.filter((_, i) => {
          const s = list[i]
          return !s || !(s.content || '').trim()
        })
        out.push({
          key: 'sections',
          label: 'All 6 sections have content',
          ok: missing.length === 0,
          detail:
            missing.length === 0
              ? 'Abstract, Introduction, Methodology, Results, Discussion, Conclusion all written.'
              : `Missing: ${missing.join(', ')}.`,
        })
      } else {
        out.push({
          key: 'sections',
          label: 'All 6 sections have content',
          ok: false,
          detail: 'Could not load manuscript sections.',
        })
      }

      // 3. At least one figure.
      const figs = settled[2]
      if (figs.status === 'fulfilled') {
        const n = figs.value.length
        out.push({
          key: 'figures',
          label: 'At least one figure uploaded',
          ok: n >= 1,
          detail: n >= 1 ? `${n} figure${n === 1 ? '' : 's'}.` : 'Upload at least one figure.',
        })
      } else {
        out.push({
          key: 'figures',
          label: 'At least one figure uploaded',
          ok: false,
          detail: 'Could not load figures.',
        })
      }

      // 4. References present.
      const arts = settled[3]
      const bib = settled[5]
      const refCount =
        arts.status === 'fulfilled'
          ? arts.value.length
          : bib.status === 'fulfilled'
            ? bib.value.entries.length
            : 0
      out.push({
        key: 'references',
        label: 'References cited',
        ok: refCount >= 1,
        detail:
          refCount >= 1
            ? `${refCount} reference${refCount === 1 ? '' : 's'} on file.`
            : 'Import articles or add references before submitting.',
      })

      // 5. Cover letter has content.
      const cv = settled[4]
      const coverOk =
        cv.status === 'fulfilled' &&
        Boolean(cv.value && (cv.value.body_html || '').trim())
      out.push({
        key: 'cover-letter',
        label: 'Cover letter drafted',
        ok: coverOk,
        detail: coverOk
          ? 'Cover letter has a body.'
          : 'Draft a cover letter (above) before submitting.',
      })

      return out
    },
    staleTime: 30_000,
  })

  return (
    <section
      data-testid="msubmission-precheck-card"
      className="rounded-2xl border border-border bg-card p-4 shadow-sm"
    >
      <div className="flex items-center gap-2">
        <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
        <span className="text-[15px] font-semibold tracking-tight">
          Pre-submission checklist
        </span>
      </div>

      {checks.isLoading && (
        <div
          data-testid="msubmission-precheck-loading"
          className="mt-3 flex items-center gap-2 text-[12px] text-muted-foreground"
        >
          <Loader2 className="h-4 w-4 animate-spin" />
          Running checks…
        </div>
      )}

      {checks.data && (
        <ul
          data-testid="msubmission-precheck-list"
          className="mt-3 space-y-2"
        >
          {checks.data.map((row) => (
            <li
              key={row.key}
              data-testid={`msubmission-precheck-${row.key}`}
              data-status={row.ok ? 'ok' : 'warn'}
              className="flex items-start gap-2 rounded-md border border-border bg-muted/20 p-2"
            >
              {row.ok ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
              ) : (
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
              )}
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-medium leading-tight">
                  {row.label}
                </div>
                <div className="mt-0.5 text-[11px] text-muted-foreground leading-snug">
                  {row.detail}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
