/**
 * NarrativeSynthesisPanel (MP19) — per-outcome row editor.
 * One row per (outcome, instrument). Direction picker maps to the arrow
 * rendered in the export table.
 */
import { Loader2, Plus, Send, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { NarrativeDirection, NarrativeSynthesisRead } from '@/lib/api'
import {
  useCreateNarrativeEntry,
  useDeleteNarrativeEntry,
  useNarrativeSynthesis,
  usePushNarrative,
  useUpdateNarrativeEntry,
} from '@/hooks/useNarrativeSynthesis'

const DIRECTIONS: { value: NarrativeDirection; label: string }[] = [
  { value: 'higher_better', label: '↑ Higher is better' },
  { value: 'lower_better', label: '↓ Lower is better' },
  { value: 'neutral', label: '· Neutral' },
]

export function NarrativeSynthesisPanel({ projectId }: { projectId: string }) {
  const list = useNarrativeSynthesis(projectId)
  const create = useCreateNarrativeEntry(projectId)
  const update = useUpdateNarrativeEntry(projectId)
  const remove = useDeleteNarrativeEntry(projectId)
  const push = usePushNarrative(projectId)

  const [outcome, setOutcome] = useState('')
  const [instrument, setInstrument] = useState('')
  const [range, setRange] = useState('')
  const [direction, setDirection] = useState<NarrativeDirection>('neutral')
  const [narrative, setNarrative] = useState('')

  const add = async () => {
    if (!outcome.trim() || !instrument.trim()) {
      toast.error('Outcome and instrument are required.')
      return
    }
    try {
      await create.mutateAsync({
        outcome_label: outcome,
        instrument,
        range_text: range || null,
        direction,
        narrative_html: narrative,
        study_citations: [],
      })
      setOutcome('')
      setInstrument('')
      setRange('')
      setNarrative('')
      toast.success('Entry added.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Add failed.')
    }
  }

  const onPush = async () => {
    try {
      await push.mutateAsync()
      toast.success('Pushed narrative synthesis table to Results.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Push failed.')
    }
  }

  return (
    <div className="space-y-6" data-testid="narrative-synthesis-panel">
      <section className="rounded-md border border-border bg-card p-4 space-y-3">
        <h3 className="text-sm font-medium">Add narrative entry</h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="ns-outcome">Outcome</Label>
            <Input
              id="ns-outcome"
              value={outcome}
              onChange={(e) => setOutcome(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="ns-instrument">Instrument</Label>
            <Input
              id="ns-instrument"
              value={instrument}
              onChange={(e) => setInstrument(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="ns-range">Range</Label>
            <Input
              id="ns-range"
              value={range}
              onChange={(e) => setRange(e.target.value)}
              placeholder="0-48"
            />
          </div>
          <div>
            <Label htmlFor="ns-dir">Direction</Label>
            <select
              id="ns-dir"
              className="mt-1 w-full rounded border border-border bg-background px-2 py-1.5 text-sm"
              value={direction}
              onChange={(e) =>
                setDirection(e.target.value as NarrativeDirection)
              }
            >
              {DIRECTIONS.map((d) => (
                <option key={d.value} value={d.value}>
                  {d.label}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div>
          <Label htmlFor="ns-narrative">Narrative</Label>
          <Textarea
            id="ns-narrative"
            value={narrative}
            onChange={(e) => setNarrative(e.target.value)}
            rows={4}
            placeholder="Across the included studies, pain scores improved by …"
          />
        </div>
        <div className="flex justify-end">
          <Button onClick={add} disabled={create.isPending}>
            {create.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <Plus className="h-4 w-4 mr-1" />
            )}
            Add
          </Button>
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Entries ({list.data?.length ?? 0})
          </h3>
          <Button
            size="sm"
            variant="outline"
            onClick={onPush}
            disabled={push.isPending || (list.data?.length ?? 0) === 0}
          >
            <Send className="h-3.5 w-3.5 mr-1" />
            Push to Results
          </Button>
        </div>
        <div className="space-y-2">
          {(list.data ?? []).map((row) => (
            <NarrativeRow
              key={row.id}
              row={row}
              onUpdate={(body) => update.mutate({ id: row.id, body })}
              onDelete={() => remove.mutate(row.id)}
            />
          ))}
        </div>
      </section>
    </div>
  )
}

function NarrativeRow({
  row,
  onUpdate,
  onDelete,
}: {
  row: NarrativeSynthesisRead
  onUpdate: (body: Partial<{ direction: NarrativeDirection }>) => void
  onDelete: () => void
}) {
  return (
    <article
      className="rounded border border-border bg-card px-4 py-3"
      data-testid={`ns-row-${row.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="text-sm font-medium">
            {row.outcome_label}
            <span className="ml-2 text-xs text-muted-foreground">
              {row.instrument}
            </span>
            {row.range_text && (
              <span className="ml-2 text-xs text-muted-foreground">
                · {row.range_text}
              </span>
            )}
          </div>
          <div
            className="prose prose-sm dark:prose-invert mt-2 max-w-none text-sm"
            dangerouslySetInnerHTML={{ __html: row.narrative_html }}
          />
        </div>
        <div className="flex flex-col gap-1 shrink-0">
          <select
            className="rounded border border-border bg-background px-1.5 py-1 text-[11px]"
            value={row.direction}
            onChange={(e) =>
              onUpdate({ direction: e.target.value as NarrativeDirection })
            }
          >
            {DIRECTIONS.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
          <Button size="sm" variant="ghost" onClick={onDelete}>
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </article>
  )
}
