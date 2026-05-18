import { Loader2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  ROB_JUDGEMENT_LABELS,
  RoBJudgementSchema,
  type RoBAssessment,
  type RoBJudgement,
  type RoBTool,
  type RoBToolDef,
} from '@/lib/api'
import { deriveOverall } from '@/lib/rob'
import { useUpdateRoB, useUpsertRoB } from '@/hooks/useReviews'

const OVERRIDE_OPTIONS: RoBJudgement[] = RoBJudgementSchema.options

export function RoBAssessmentForm({
  projectId,
  articleId,
  tool,
  toolDef,
  existing,
  onSaved,
}: {
  projectId: string
  articleId: string
  tool: RoBTool
  toolDef: RoBToolDef
  existing?: RoBAssessment
  onSaved?: () => void
}) {
  const upsert = useUpsertRoB(projectId)
  const update = useUpdateRoB(projectId)

  const [answers, setAnswers] = useState<Record<string, string>>(
    () => existing?.domain_answers ?? {},
  )
  const [override, setOverride] = useState<RoBJudgement | ''>(
    (existing?.overall_override as RoBJudgement | null) ?? '',
  )
  const [notes, setNotes] = useState(existing?.notes ?? '')

  // If the user switches tool, reset domain answers (different keys).
  useEffect(() => {
    if (existing && existing.tool === tool) {
      setAnswers(existing.domain_answers)
      setOverride((existing.overall_override as RoBJudgement | null) ?? '')
      setNotes(existing.notes ?? '')
    } else {
      setAnswers({})
      setOverride('')
    }
  }, [tool, existing])

  const criticalKeys = useMemo(
    () => new Set(toolDef.domains.filter((d) => d.critical).map((d) => d.key)),
    [toolDef],
  )

  const overallAuto = useMemo(
    () => deriveOverall(tool, answers, criticalKeys),
    [tool, answers, criticalKeys],
  )

  const allAnswered =
    toolDef.domains.length > 0 &&
    toolDef.domains.every((d) => !!answers[d.key])

  function save() {
    if (!allAnswered) {
      toast.error('Please answer every domain before saving.')
      return
    }

    if (existing && existing.tool === tool) {
      update.mutate(
        {
          id: existing.id,
          body: {
            domain_answers: answers,
            overall_override: (override || null) as RoBJudgement | null,
            notes: notes.trim() || null,
          },
        },
        {
          onSuccess: () => {
            toast.success('Risk of bias saved')
            onSaved?.()
          },
          onError: (e: Error) => toast.error(e.message),
        },
      )
      return
    }

    upsert.mutate(
      {
        article_id: articleId,
        tool,
        domain_answers: answers,
        notes: notes.trim() || null,
      },
      {
        onSuccess: (created) => {
          if (override) {
            update.mutate({
              id: created.id,
              body: { overall_override: override as RoBJudgement },
            })
          }
          toast.success('Risk of bias saved')
          onSaved?.()
        },
        onError: (e: Error) => toast.error(e.message),
      },
    )
  }

  return (
    <div className="space-y-5">
      <ol className="space-y-3">
        {toolDef.domains.map((d, idx) => (
          <li
            key={d.key}
            className="rounded-md border border-border bg-white px-3 py-3 space-y-2"
          >
            <div>
              <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                Domain {idx + 1}
                {d.critical && (
                  <span className="ml-2 text-rose-600 text-[10px] font-medium">
                    CRITICAL
                  </span>
                )}
              </div>
              <div className="text-[13px] font-medium mt-0.5">{d.label}</div>
              <div className="text-[12px] text-muted-foreground mt-0.5">
                {d.question}
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {d.answers.map((ans) => {
                const active = answers[d.key] === ans
                return (
                  <button
                    key={ans}
                    type="button"
                    onClick={() => setAnswers((a) => ({ ...a, [d.key]: ans }))}
                    className={
                      'px-2.5 h-7 rounded-md text-[11px] font-medium border transition-colors ' +
                      (active
                        ? 'border-accent bg-accent text-white'
                        : 'border-border bg-muted/20 hover:bg-muted/40 text-foreground')
                    }
                    aria-pressed={active}
                  >
                    {ans}
                  </button>
                )
              })}
            </div>
          </li>
        ))}
      </ol>

      <div className="rounded-md border border-accent/30 bg-accent/[0.04] px-3 py-2.5">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
              Live overall (auto)
            </div>
            <div className="mt-0.5 text-[13px] font-semibold">
              {ROB_JUDGEMENT_LABELS[overallAuto]}
            </div>
          </div>
          <div className="space-y-1 min-w-[180px]">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
              Manual override
            </div>
            <Select
              value={override}
              onValueChange={(v) => setOverride(v as RoBJudgement | '')}
            >
              <SelectTrigger className="h-8 text-[12px]">
                <SelectValue placeholder="Use automatic" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">Use automatic</SelectItem>
                {OVERRIDE_OPTIONS.map((j) => (
                  <SelectItem key={j} value={j}>
                    {ROB_JUDGEMENT_LABELS[j]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </div>

      <div className="space-y-1">
        <label className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Notes
        </label>
        <Textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Optional reviewer notes"
          rows={3}
        />
      </div>

      <div className="flex justify-end">
        <Button
          onClick={save}
          disabled={upsert.isPending || update.isPending}
          className="bg-accent hover:bg-accent-hover text-white"
        >
          {(upsert.isPending || update.isPending) && (
            <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
          )}
          Save assessment
        </Button>
      </div>
    </div>
  )
}
