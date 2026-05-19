import { Loader2, Play, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { LivingHitDecision, LivingSchedule } from '@/lib/api'
import {
  useDeleteLivingReview,
  useImportLivingReviewHit,
  useLivingReview,
  useLivingReviewHits,
  useRunLivingReviewNow,
  useUpdateLivingReviewHit,
  useUpsertLivingReview,
} from '@/hooks/useLivingReview'

const SCHEDULES: { value: LivingSchedule; label: string; help: string }[] = [
  { value: 'daily', label: 'Daily', help: 'Runs every day at 02:00 UTC' },
  { value: 'weekly', label: 'Weekly', help: 'Runs Mondays at 02:00 UTC' },
  { value: 'monthly', label: 'Monthly', help: 'Runs on the 1st at 02:00 UTC' },
]

const DECISIONS: { value: LivingHitDecision | undefined; label: string }[] = [
  { value: 'new', label: 'New' },
  { value: 'accepted', label: 'Accepted' },
  { value: 'dismissed', label: 'Dismissed' },
  { value: undefined, label: 'All' },
]

export function LivingReviewPanel({ projectId }: { projectId: string }) {
  const { data: job, isLoading } = useLivingReview(projectId)
  const upsert = useUpsertLivingReview(projectId)
  const patchDelete = useDeleteLivingReview(projectId)
  const runNow = useRunLivingReviewNow(projectId)

  const [query, setQuery] = useState('')
  const [schedule, setSchedule] = useState<LivingSchedule>('weekly')
  const [enabled, setEnabled] = useState(true)

  useEffect(() => {
    if (job) {
      setQuery(job.pubmed_query)
      setSchedule(job.schedule)
      setEnabled(job.enabled)
    }
  }, [job?.id, job?.pubmed_query, job?.schedule, job?.enabled])

  const onSave = async () => {
    if (!query.trim()) {
      toast.error('Enter a PubMed query first.')
      return
    }
    try {
      await upsert.mutateAsync({
        pubmed_query: query.trim(),
        schedule,
        enabled,
      })
      toast.success('Living review saved.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not save')
    }
  }

  const onRunNow = async () => {
    try {
      const result = await runNow.mutateAsync()
      toast.success(
        result.new_hits > 0
          ? `Found ${result.new_hits} new hit${result.new_hits === 1 ? '' : 's'}.`
          : 'No new hits — your library is up to date.',
      )
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Run failed')
    }
  }

  const onDelete = async () => {
    if (!job) return
    if (!confirm('Delete this living-review job and all its hit history?')) return
    try {
      await patchDelete.mutateAsync()
      setQuery('')
      setSchedule('weekly')
      setEnabled(true)
      toast.success('Living review deleted.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not delete')
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h3 className="text-[15px] font-semibold tracking-tight">Living review</h3>
        <div className="text-[12px] text-muted-foreground">
          Re-run a saved PubMed query on a cron schedule and triage new
          studies as they appear. Hits are kept until you accept or dismiss
          them.
        </div>
      </header>

      {isLoading ? (
        <div className="text-[12px] text-muted-foreground">Loading…</div>
      ) : (
        <SetupCard
          query={query}
          schedule={schedule}
          enabled={enabled}
          isSaved={!!job}
          isSaving={upsert.isPending}
          isRunning={runNow.isPending}
          lastRunAt={job?.last_run_at ?? null}
          lastHitCount={job?.last_hit_count ?? null}
          onQueryChange={setQuery}
          onScheduleChange={setSchedule}
          onEnabledChange={setEnabled}
          onSave={onSave}
          onRunNow={onRunNow}
          onDelete={onDelete}
        />
      )}

      {job && <HitsList projectId={projectId} />}
    </div>
  )
}

function SetupCard(props: {
  query: string
  schedule: LivingSchedule
  enabled: boolean
  isSaved: boolean
  isSaving: boolean
  isRunning: boolean
  lastRunAt: string | null
  lastHitCount: number | null
  onQueryChange: (v: string) => void
  onScheduleChange: (v: LivingSchedule) => void
  onEnabledChange: (v: boolean) => void
  onSave: () => void
  onRunNow: () => void
  onDelete: () => void
}) {
  return (
    <div className="rounded-md border border-border bg-white p-5 space-y-4">
      <div>
        <Label
          htmlFor="living-review-query"
          className="text-[12px] uppercase tracking-wider text-muted-foreground font-medium"
        >
          PubMed query
        </Label>
        <Textarea
          id="living-review-query"
          value={props.query}
          onChange={(e) => props.onQueryChange(e.target.value)}
          placeholder='e.g. ("aspirin"[Title/Abstract]) AND ("stroke"[Mesh])'
          rows={3}
          className="mt-1.5 font-mono text-[12px]"
        />
      </div>

      <fieldset>
        <legend className="text-[12px] uppercase tracking-wider text-muted-foreground font-medium">
          Schedule
        </legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {SCHEDULES.map((s) => (
            <label
              key={s.value}
              className={`flex-1 min-w-[140px] rounded-md border px-3 py-2 cursor-pointer transition-colors ${
                props.schedule === s.value
                  ? 'border-accent bg-accent/10'
                  : 'border-border hover:border-muted-foreground'
              }`}
            >
              <div className="flex items-center gap-2">
                <input
                  type="radio"
                  name="living-schedule"
                  value={s.value}
                  checked={props.schedule === s.value}
                  onChange={() => props.onScheduleChange(s.value)}
                  className="accent-accent"
                />
                <span className="text-[13px] font-medium">{s.label}</span>
              </div>
              <div className="mt-1 text-[11px] text-muted-foreground pl-6">
                {s.help}
              </div>
            </label>
          ))}
        </div>
      </fieldset>

      <label className="flex items-center gap-2 text-[13px]">
        <input
          type="checkbox"
          checked={props.enabled}
          onChange={(e) => props.onEnabledChange(e.target.checked)}
          className="accent-accent"
        />
        <span>Enabled — pauses automatic reruns when off</span>
      </label>

      <div className="flex flex-wrap items-center gap-2 pt-1">
        <Button onClick={props.onSave} disabled={props.isSaving}>
          {props.isSaving ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : props.isSaved ? (
            'Save changes'
          ) : (
            'Save'
          )}
        </Button>
        <Button
          variant="outline"
          onClick={props.onRunNow}
          disabled={props.isRunning || !props.isSaved}
        >
          {props.isRunning ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <>
              <Play className="h-3.5 w-3.5 mr-1.5" /> Run now
            </>
          )}
        </Button>
        {props.isSaved && (
          <Button
            variant="ghost"
            className="text-destructive hover:text-destructive ml-auto"
            onClick={props.onDelete}
          >
            <Trash2 className="h-3.5 w-3.5 mr-1.5" /> Delete
          </Button>
        )}
      </div>

      {props.isSaved && (
        <div className="border-t border-border pt-3 text-[11px] text-muted-foreground flex flex-wrap items-center gap-x-4 gap-y-1">
          <span>
            Last run:{' '}
            <span className="font-medium text-foreground">
              {props.lastRunAt ? new Date(props.lastRunAt).toLocaleString() : 'never'}
            </span>
          </span>
          <span>
            Last batch:{' '}
            <span className="font-medium text-foreground">
              {props.lastHitCount ?? 0} new
            </span>
          </span>
        </div>
      )}
    </div>
  )
}

function HitsList({ projectId }: { projectId: string }) {
  const [decision, setDecision] = useState<LivingHitDecision | undefined>('new')
  const { data: hits = [], isLoading } = useLivingReviewHits(projectId, decision)
  const update = useUpdateLivingReviewHit(projectId)
  const importHit = useImportLivingReviewHit(projectId)

  const newCount = useLivingReviewHits(projectId, 'new').data?.length ?? 0

  const onAccept = async (hitId: string) => {
    try {
      await update.mutateAsync({ hitId, decision: 'accepted' })
      await importHit.mutateAsync(hitId)
      toast.success('Imported as article.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Import failed')
    }
  }

  const onDismiss = async (hitId: string) => {
    try {
      await update.mutateAsync({ hitId, decision: 'dismissed' })
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Could not dismiss')
    }
  }

  return (
    <section className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-[13px] font-semibold tracking-tight">Hits</h4>
          <div className="text-[11px] text-muted-foreground">
            {newCount > 0 && (
              <span className="mr-2 rounded-full bg-accent/15 text-accent px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider">
                {newCount} new
              </span>
            )}
            Accept to import as an Article; dismiss to suppress future
            notifications for this PMID.
          </div>
        </div>
        <div className="flex gap-1 text-[11px]">
          {DECISIONS.map((d) => (
            <button
              key={d.label}
              onClick={() => setDecision(d.value)}
              className={`rounded-md border px-2 py-1 ${
                decision === d.value
                  ? 'border-accent bg-accent/10 text-foreground'
                  : 'border-border text-muted-foreground hover:text-foreground'
              }`}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="text-[12px] text-muted-foreground">Loading…</div>
      ) : hits.length === 0 ? (
        <div className="rounded-md border border-dashed border-border p-6 text-center text-[12px] text-muted-foreground">
          No hits in this view.
        </div>
      ) : (
        <ul className="divide-y divide-border rounded-md border border-border bg-white">
          {hits.map((h) => (
            <li
              key={h.id}
              className="px-4 py-3 flex items-start gap-3 text-[13px]"
            >
              <div className="min-w-0 flex-1">
                <div className="font-medium truncate" title={h.title}>
                  {h.title}
                </div>
                <div className="text-[11px] text-muted-foreground">
                  PMID {h.pmid} · seen {new Date(h.run_at).toLocaleDateString()}
                </div>
              </div>
              {h.decision === 'new' ? (
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onDismiss(h.id)}
                  >
                    Dismiss
                  </Button>
                  <Button size="sm" onClick={() => onAccept(h.id)}>
                    Accept
                  </Button>
                </div>
              ) : (
                <span className="text-[11px] uppercase tracking-wider text-muted-foreground self-center">
                  {h.decision}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
