import { Check, HelpCircle, Loader2, MessageSquareText, Sparkles, X } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import {
  EXCLUSION_CATEGORY_LABELS,
  ExclusionCategorySchema,
  type ExclusionCategory,
  type ReviewStage,
  type ScreeningDecision,
  type ScreeningRecord,
} from '@/lib/api'
import { cn } from '@/lib/utils'
import {
  useAiSuggestScreening,
  useUpdateScreening,
  useUpsertScreening,
} from '@/hooks/useReviews'

const EXCLUSION_OPTIONS: ExclusionCategory[] = ExclusionCategorySchema.options

export function ScreeningRowActions({
  projectId,
  articleId,
  stage,
  record,
}: {
  projectId: string
  articleId: string
  stage: ReviewStage
  record: ScreeningRecord | undefined
}) {
  const upsert = useUpsertScreening(projectId)
  const update = useUpdateScreening(projectId)
  const aiSuggest = useAiSuggestScreening(projectId)

  const decision = (record?.decision ?? 'pending') as ScreeningDecision
  const reason = record?.reason ?? ''
  const exclusion = (record?.exclusion_category ?? null) as ExclusionCategory | null

  function setDecision(next: ScreeningDecision) {
    if (record) {
      update.mutate(
        { id: record.id, body: { decision: next } },
        { onError: (e: Error) => toast.error(e.message) },
      )
    } else {
      upsert.mutate(
        { article_id: articleId, stage, decision: next },
        { onError: (e: Error) => toast.error(e.message) },
      )
    }
  }

  function setReason(next: string) {
    if (record) {
      update.mutate({ id: record.id, body: { reason: next || null } })
    } else {
      upsert.mutate({
        article_id: articleId,
        stage,
        decision: 'pending',
        reason: next || null,
      })
    }
  }

  function setExclusion(cat: ExclusionCategory | null) {
    if (record) {
      update.mutate({ id: record.id, body: { exclusion_category: cat } })
    } else {
      upsert.mutate({
        article_id: articleId,
        stage,
        decision: 'exclude',
        exclusion_category: cat,
      })
    }
  }

  function suggest() {
    let id = record?.id
    const run = (sid: string) =>
      aiSuggest.mutate(sid, {
        onSuccess: () => toast.success('AI suggestion ready'),
        onError: (e: Error) => toast.error(e.message),
      })
    if (id) {
      run(id)
      return
    }
    upsert.mutate(
      { article_id: articleId, stage, decision: 'pending' },
      {
        onSuccess: (created) => run(created.id),
        onError: (e: Error) => toast.error(e.message),
      },
    )
  }

  const aiSuggestion = record?.ai_suggestion as
    | { vote?: string; reason?: string; model?: string }
    | null
    | undefined

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-1.5 flex-wrap">
        <DecisionBtn
          active={decision === 'include'}
          tone="emerald"
          icon={<Check className="h-3.5 w-3.5" />}
          label="Include"
          onClick={() => setDecision('include')}
        />
        <DecisionBtn
          active={decision === 'exclude'}
          tone="rose"
          icon={<X className="h-3.5 w-3.5" />}
          label="Exclude"
          onClick={() => setDecision('exclude')}
        />
        <DecisionBtn
          active={decision === 'maybe'}
          tone="amber"
          icon={<HelpCircle className="h-3.5 w-3.5" />}
          label="Maybe"
          onClick={() => setDecision('maybe')}
        />
        <Popover>
          <PopoverTrigger asChild>
            <Button
              size="icon"
              variant="ghost"
              className="h-7 w-7"
              aria-label="Edit reason"
            >
              <MessageSquareText
                className={cn(
                  'h-3.5 w-3.5',
                  reason ? 'text-accent' : 'text-muted-foreground',
                )}
              />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-[280px]">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Reason / note
            </div>
            <Textarea
              defaultValue={reason}
              onBlur={(e) => {
                if (e.target.value !== reason) setReason(e.target.value)
              }}
              placeholder="Optional reasoning for this decision"
              rows={3}
              className="mt-2 text-[12px]"
            />
          </PopoverContent>
        </Popover>
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7"
          onClick={suggest}
          disabled={aiSuggest.isPending}
          aria-label="AI suggest screening"
        >
          {aiSuggest.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" />
          ) : (
            <Sparkles className="h-3.5 w-3.5 text-accent" />
          )}
        </Button>
      </div>

      {stage === 'full_text' && decision === 'exclude' && (
        <Select
          value={exclusion ?? ''}
          onValueChange={(v) => setExclusion((v || null) as ExclusionCategory | null)}
        >
          <SelectTrigger className="h-7 text-[12px] w-[180px]">
            <SelectValue placeholder="Exclusion category" />
          </SelectTrigger>
          <SelectContent>
            {EXCLUSION_OPTIONS.map((c) => (
              <SelectItem key={c} value={c}>
                {EXCLUSION_CATEGORY_LABELS[c]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {aiSuggestion?.vote && (
        <div className="flex items-start gap-2 rounded-md border border-accent/20 bg-accent/[0.04] px-2.5 py-1.5">
          <Sparkles className="h-3 w-3 mt-0.5 text-accent shrink-0" />
          <div className="text-[11px] leading-tight">
            <span className="text-muted-foreground">AI suggests </span>
            <Badge variant="outline" className="ml-0.5 text-[10px] py-0 px-1.5">
              {aiSuggestion.vote}
            </Badge>
            {aiSuggestion.reason && (
              <div className="text-muted-foreground mt-0.5">{aiSuggestion.reason}</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function DecisionBtn({
  active,
  tone,
  icon,
  label,
  onClick,
}: {
  active: boolean
  tone: 'emerald' | 'rose' | 'amber'
  icon: React.ReactNode
  label: string
  onClick: () => void
}) {
  const tones: Record<typeof tone, string> = {
    emerald: 'border-emerald-300 bg-emerald-50 text-emerald-700',
    rose: 'border-rose-300 bg-rose-50 text-rose-700',
    amber: 'border-amber-300 bg-amber-50 text-amber-800',
  }
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'inline-flex items-center gap-1 px-2 h-7 rounded-md border text-[11px] font-medium transition-colors',
        active
          ? tones[tone]
          : 'border-border bg-white text-muted-foreground hover:bg-muted/40',
      )}
      aria-pressed={active}
    >
      {icon}
      {label}
    </button>
  )
}
