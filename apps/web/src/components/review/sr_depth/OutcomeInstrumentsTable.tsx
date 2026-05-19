/**
 * OutcomeInstrumentsTable (MP19) — many-to-many studies × instruments
 * matrix. Rows are instruments, study_values is the per-study cell list.
 */
import { Loader2, Plus, Send, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { OutcomeInstrumentRead } from '@/lib/api'
import {
  useCreateOutcomeInstrument,
  useDeleteOutcomeInstrument,
  useOutcomeInstruments,
  usePushOutcomeInstruments,
} from '@/hooks/useOutcomeInstruments'

export function OutcomeInstrumentsTable({ projectId }: { projectId: string }) {
  const list = useOutcomeInstruments(projectId)
  const create = useCreateOutcomeInstrument(projectId)
  const remove = useDeleteOutcomeInstrument(projectId)
  const push = usePushOutcomeInstruments(projectId)

  const [outcome, setOutcome] = useState('')
  const [instrument, setInstrument] = useState('')
  const [low, setLow] = useState('')
  const [high, setHigh] = useState('')
  const [mid, setMid] = useState('')

  const add = async () => {
    if (!outcome.trim() || !instrument.trim()) {
      toast.error('Outcome and instrument are required.')
      return
    }
    try {
      await create.mutateAsync({
        outcome_label: outcome,
        instrument_name: instrument,
        score_range_low: low ? Number(low) : null,
        score_range_high: high ? Number(high) : null,
        mid: mid ? Number(mid) : null,
        study_values: [],
      })
      setOutcome('')
      setInstrument('')
      setLow('')
      setHigh('')
      setMid('')
      toast.success('Instrument row added.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Add failed.')
    }
  }

  return (
    <div className="space-y-6" data-testid="outcome-instruments-table">
      <section className="rounded-md border border-border bg-card p-4 space-y-3">
        <h3 className="text-sm font-medium">Add instrument row</h3>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="oi-out">Outcome</Label>
            <Input
              id="oi-out"
              value={outcome}
              onChange={(e) => setOutcome(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="oi-ins">Instrument name</Label>
            <Input
              id="oi-ins"
              value={instrument}
              onChange={(e) => setInstrument(e.target.value)}
              placeholder="OKS, KSS, VAS…"
            />
          </div>
          <div>
            <Label htmlFor="oi-low">Range low</Label>
            <Input
              id="oi-low"
              type="number"
              value={low}
              onChange={(e) => setLow(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="oi-high">Range high</Label>
            <Input
              id="oi-high"
              type="number"
              value={high}
              onChange={(e) => setHigh(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="oi-mid">MID</Label>
            <Input
              id="oi-mid"
              type="number"
              value={mid}
              onChange={(e) => setMid(e.target.value)}
            />
          </div>
        </div>
        <div className="flex justify-end">
          <Button onClick={add} disabled={create.isPending}>
            {create.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <Plus className="h-4 w-4 mr-1" />
            )}
            Add row
          </Button>
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Instruments ({list.data?.length ?? 0})
          </h3>
          <Button
            size="sm"
            variant="outline"
            onClick={() => push.mutate()}
            disabled={push.isPending}
          >
            <Send className="h-3.5 w-3.5 mr-1" />
            Push to Results
          </Button>
        </div>
        <div className="space-y-2">
          {(list.data ?? []).map((row) => (
            <InstrumentRow
              key={row.id}
              row={row}
              onDelete={() => remove.mutate(row.id)}
            />
          ))}
        </div>
      </section>
    </div>
  )
}

function InstrumentRow({
  row,
  onDelete,
}: {
  row: OutcomeInstrumentRead
  onDelete: () => void
}) {
  return (
    <article
      className="rounded border border-border bg-card px-4 py-3 text-sm"
      data-testid={`oi-row-${row.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="font-medium">
            {row.outcome_label}
            <span className="ml-2 text-xs text-muted-foreground">
              {row.instrument_name}
            </span>
          </div>
          <div className="mt-1 text-[12px] text-muted-foreground">
            {row.score_range_low ?? '-'} – {row.score_range_high ?? '-'}
            {row.mid !== null && row.mid !== undefined && (
              <> · MID {row.mid}</>
            )}
            {' · '}
            {row.study_values.length} study cell
            {row.study_values.length === 1 ? '' : 's'}
          </div>
        </div>
        <Button size="sm" variant="ghost" onClick={onDelete}>
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </article>
  )
}
