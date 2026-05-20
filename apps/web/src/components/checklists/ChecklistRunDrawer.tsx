import { Sparkles } from 'lucide-react'
import { useMemo, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
import {
  useAutoCheckRun,
  useChecklistRun,
  usePatchChecklistItem,
} from '@/hooks/useChecklists'
import type { ChecklistItemStatus, ChecklistRunItem } from '@/lib/api'

import { ChecklistComplianceBar } from './ChecklistComplianceBar'
import { ChecklistExportButton } from './ChecklistExportButton'

export type ChecklistRunDrawerProps = {
  projectId: string
  runId: string
}

const STATUSES: { value: ChecklistItemStatus; label: string; tone: string }[] = [
  { value: 'pass', label: 'Pass', tone: 'bg-emerald-100 text-emerald-800' },
  { value: 'fail', label: 'Fail', tone: 'bg-rose-100 text-rose-800' },
  { value: 'unclear', label: 'Unclear', tone: 'bg-amber-100 text-amber-800' },
  { value: 'na', label: 'N/A', tone: 'bg-zinc-100 text-zinc-800' },
]

const SECTIONS: readonly string[] = [
  'Title',
  'Abstract',
  'Introduction',
  'Methodology',
  'Results',
  'Discussion',
  'Conclusion',
  'Other',
]

/**
 * MP20 — Right pane: editable view of a single checklist run.
 *
 * For each item, the user picks pass / fail / unclear / N/A from a radio
 * group, types a comment, and (optionally) overrides which manuscript
 * section the item is mapped to. An "Auto-check" button at the top runs
 * the best-effort heuristic on the whole run.
 */
export function ChecklistRunDrawer({ projectId, runId }: ChecklistRunDrawerProps) {
  const { data: run, isLoading } = useChecklistRun(projectId, runId)
  const patch = usePatchChecklistItem(projectId, runId)
  const autoCheck = useAutoCheckRun(projectId, runId)

  const counts = useMemo(() => {
    const items = run?.items ?? []
    return {
      pass: items.filter((i) => i.status === 'pass').length,
      fail: items.filter((i) => i.status === 'fail').length,
      unclear: items.filter((i) => i.status === 'unclear').length,
      na: items.filter((i) => i.status === 'na').length,
      total: items.length,
    }
  }, [run])

  if (isLoading || !run) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Loading checklist…
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col" data-testid="checklist-run-drawer">
      <div className="border-b px-3 py-2">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="truncate text-sm uppercase text-muted-foreground">
              {run.checklist_key.replace(/_/g, ' ')}
            </div>
            <h2 className="truncate text-lg font-semibold">{run.title}</h2>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => autoCheck.mutate()}
              disabled={autoCheck.isPending}
              data-testid="checklist-auto-check-btn"
            >
              <Sparkles className="mr-1 h-4 w-4" />
              {autoCheck.isPending ? 'Auto-checking…' : 'Auto-check'}
            </Button>
            <ChecklistExportButton
              projectId={projectId}
              runId={runId}
              filenameBase={`${run.checklist_key.toLowerCase()}-${run.title
                .toLowerCase()
                .replace(/[^a-z0-9-]+/g, '-')
                .replace(/^-+|-+$/g, '')}`}
            />
          </div>
        </div>
        <div className="mt-2">
          <ChecklistComplianceBar
            pct={run.overall_compliance_pct}
            passCount={counts.pass}
            failCount={counts.fail}
            unclearCount={counts.unclear}
            naCount={counts.na}
            totalCount={counts.total}
          />
        </div>
      </div>
      <ScrollArea className="flex-1">
        <ul className="divide-y">
          {run.items.map((item) => (
            <li
              key={item.item_id}
              className="px-3 py-3"
              data-testid={`checklist-item-row-${item.item_id}`}
            >
              <ItemRow
                item={item}
                onStatus={(status) =>
                  patch.mutate({ itemId: item.item_id, patch: { status } })
                }
                onComment={(comment) =>
                  patch.mutate({ itemId: item.item_id, patch: { comment } })
                }
                onSection={(mapped_section) =>
                  patch.mutate({
                    itemId: item.item_id,
                    patch: { mapped_section: mapped_section || null },
                  })
                }
              />
            </li>
          ))}
        </ul>
      </ScrollArea>
    </div>
  )
}

function ItemRow({
  item,
  onStatus,
  onComment,
  onSection,
}: {
  item: ChecklistRunItem
  onStatus: (s: ChecklistItemStatus) => void
  onComment: (c: string) => void
  onSection: (s: string) => void
}) {
  const [comment, setComment] = useState(item.comment ?? '')

  const commitComment = () => {
    if (comment !== item.comment) onComment(comment)
  }

  return (
    <div className="space-y-2">
      <div className="flex items-start gap-2">
        <Badge variant="outline" className="shrink-0">
          {item.item_id}
        </Badge>
        <div className="text-sm font-medium">{item.item_text}</div>
      </div>
      {item.mapped_text_excerpt && (
        <div className="rounded-md border bg-muted/30 px-2 py-1 text-xs italic">
          <span className="font-semibold">{item.mapped_section}:</span>{' '}
          {item.mapped_text_excerpt}
        </div>
      )}
      <div
        role="radiogroup"
        aria-label={`Status for item ${item.item_id}`}
        className="flex flex-wrap gap-1"
      >
        {STATUSES.map((s) => {
          const selected = item.status === s.value
          return (
            <button
              key={s.value}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onStatus(s.value)}
              data-testid={`status-${item.item_id}-${s.value}`}
              className={`rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-border ${
                selected ? s.tone : 'bg-background hover:bg-muted'
              }`}
            >
              {s.label}
            </button>
          )
        })}
      </div>
      <div className="flex flex-wrap gap-2 sm:flex-nowrap sm:items-start">
        <div className="w-full sm:w-48 shrink-0">
          <Select
            value={item.mapped_section ?? ''}
            onValueChange={(v) => onSection(v === '__none__' ? '' : v)}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Map to section…" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">— No mapping —</SelectItem>
              {SECTIONS.map((s) => (
                <SelectItem key={s} value={s}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          onBlur={commitComment}
          placeholder="Reviewer comments…"
          rows={2}
          className="min-h-[2.25rem] text-xs"
          data-testid={`checklist-comment-${item.item_id}`}
        />
      </div>
    </div>
  )
}
