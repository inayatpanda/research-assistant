/**
 * Phase 16 (MP16) — Figure numbering panel.
 *
 * Shows the current figure order with their resolved numbers + an
 * "Auto-renumber by first reference" button. Manual drag-to-reorder is
 * intentionally NOT included here — the FiguresPanel already owns
 * dnd-kit drag handling and re-uses the same ``figuresApi.reorder``
 * pipeline. This panel is the read-only counterpart that surfaces the
 * numbering result and lets the user trigger the auto-pass.
 */
import { Loader2, Wand2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { figuresApi, type Figure } from '@/lib/api'

export function FigureNumberingPanel({
  projectId,
  figures,
  onAfterRenumber,
}: {
  projectId: string
  figures: Figure[]
  onAfterRenumber?: (next: Figure[]) => void
}) {
  const [busy, setBusy] = useState(false)

  async function onRenumber() {
    setBusy(true)
    try {
      const next = await figuresApi.renumber(projectId)
      toast.success(`Renumbered ${next.length} figure${next.length === 1 ? '' : 's'}`)
      onAfterRenumber?.(next)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Renumber failed')
    } finally {
      setBusy(false)
    }
  }

  if (figures.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-border bg-muted/20 p-4 text-[12px] text-muted-foreground">
        Upload figures to enable auto-numbering.
      </div>
    )
  }

  return (
    <div className="space-y-3" data-testid="figure-numbering-panel">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-[12px] font-semibold text-foreground">
          Figure numbering
        </h3>
        <Button
          size="sm"
          variant="outline"
          onClick={onRenumber}
          disabled={busy}
          className="h-7 text-[11px]"
        >
          {busy ? (
            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
          ) : (
            <Wand2 className="h-3 w-3 mr-1" />
          )}
          Auto-renumber
        </Button>
      </div>
      <ol className="space-y-1 text-[12px]" aria-label="Current figure order">
        {figures.map((f) => (
          <li
            key={f.id}
            className="flex items-center gap-2 rounded-md border border-border bg-white px-2.5 py-1.5"
          >
            <span className="font-mono text-muted-foreground w-12">
              Figure {f.figure_number}
            </span>
            <span className="truncate flex-1 text-foreground">
              {f.caption || (
                <span className="italic text-muted-foreground">
                  (no caption)
                </span>
              )}
            </span>
          </li>
        ))}
      </ol>
      <p className="text-[10px] text-muted-foreground">
        Auto-renumber re-orders figures by the first in-text reference order
        in your manuscript sections. Figures without a reference are
        appended in their current order.
      </p>
    </div>
  )
}
