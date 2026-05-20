import { useState } from 'react'
import { Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { CostColumnBinding, EconomicCostRole } from '@/lib/api'

export interface CostColumnBinderProps {
  /** Available dataset columns to bind. */
  availableColumns: string[]
  /** Existing bindings. */
  bindings: CostColumnBinding[]
  /** Called when the user changes the binding list. */
  onChange: (next: CostColumnBinding[]) => void
}

const ROLES: { value: EconomicCostRole; label: string; help: string }[] = [
  { value: 'cost_total', label: 'Total cost', help: 'Per-patient total cost' },
  { value: 'unit_cost', label: 'Unit cost', help: 'Cost per resource' },
  { value: 'quantity', label: 'Quantity', help: 'Resource quantity' },
  { value: 'utility_score', label: 'Utility score', help: 'EQ-5D/SF-6D utility per timepoint' },
  { value: 'qaly_weight', label: 'QALY weight', help: 'Pre-computed QALY per patient' },
  { value: 'time_to_event', label: 'Time-to-event', help: 'Timepoint (months) for AUC QALY' },
]

/**
 * MP18 — Bind dataset variables to economic roles.
 *
 * NOT actually drag-and-drop (we keep the API minimal); rendered as a
 * list of (column, role) rows. Drop-target affordances are added via
 * the parent's wizard step labelling.
 */
export function CostColumnBinder({
  availableColumns,
  bindings,
  onChange,
}: CostColumnBinderProps) {
  const [draftCol, setDraftCol] = useState<string>(availableColumns[0] ?? '')
  const [draftRole, setDraftRole] = useState<EconomicCostRole>('cost_total')

  const handleAdd = () => {
    if (!draftCol) return
    onChange([...bindings, { col: draftCol, role: draftRole }])
  }
  const handleRemove = (idx: number) => {
    onChange(bindings.filter((_, i) => i !== idx))
  }

  return (
    <div data-testid="cost-column-binder" className="space-y-3">
      <div className="text-sm text-muted-foreground">
        Bind each dataset column to its economic role.
      </div>
      {bindings.length === 0 ? (
        <div className="text-sm italic text-muted-foreground">
          No bindings yet — at least <strong>Total cost</strong> + one of{' '}
          <strong>QALY weight</strong> or (<strong>Utility</strong> +{' '}
          <strong>Time-to-event</strong>) is required to run the analysis.
        </div>
      ) : (
        <ul className="space-y-2">
          {bindings.map((b, idx) => (
            <li
              key={`${b.col}-${b.role}-${idx}`}
              className="flex items-center justify-between gap-2 rounded-md border border-border bg-muted/30 px-3 py-2"
            >
              <div className="flex items-center gap-2 text-sm">
                <code className="rounded bg-background px-1.5 py-0.5">
                  {b.col}
                </code>
                <span className="text-muted-foreground">→</span>
                <span className="font-medium">
                  {ROLES.find((r) => r.value === b.role)?.label ?? b.role}
                </span>
              </div>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleRemove(idx)}
                aria-label={`Remove binding ${b.col} → ${b.role}`}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </li>
          ))}
        </ul>
      )}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2 items-end">
        <div>
          <Label htmlFor="binder-col">Column</Label>
          <Select value={draftCol} onValueChange={setDraftCol}>
            <SelectTrigger id="binder-col"><SelectValue /></SelectTrigger>
            <SelectContent>
              {availableColumns.map((c) => (
                <SelectItem key={c} value={c}>{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label htmlFor="binder-role">Role</Label>
          <Select
            value={draftRole}
            onValueChange={(v) => setDraftRole(v as EconomicCostRole)}
          >
            <SelectTrigger id="binder-role"><SelectValue /></SelectTrigger>
            <SelectContent>
              {ROLES.map((r) => (
                <SelectItem key={r.value} value={r.value}>
                  {r.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button type="button" onClick={handleAdd} disabled={!draftCol}>
          Add binding
        </Button>
      </div>
    </div>
  )
}
