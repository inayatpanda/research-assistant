import { Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  useChecklistRuns,
  useDeleteChecklistRun,
} from '@/hooks/useChecklists'
import type { ChecklistRunSummary } from '@/lib/api'

export type ChecklistRunsListProps = {
  projectId: string
  activeRunId: string | null
  onSelect: (runId: string) => void
}

/**
 * MP20 — Middle pane: project-scoped list of in-progress checklist runs.
 *
 * Each row shows the title + the originating catalogue + the compliance
 * percentage. Clicking selects the run; the trash icon deletes it.
 */
export function ChecklistRunsList({
  projectId,
  activeRunId,
  onSelect,
}: ChecklistRunsListProps) {
  const { data: runs = [], isLoading } = useChecklistRuns(projectId)
  const deleteMutation = useDeleteChecklistRun(projectId)

  const onDelete = (e: React.MouseEvent, runId: string) => {
    e.stopPropagation()
    if (confirm('Delete this checklist run?')) {
      deleteMutation.mutate(runId)
    }
  }

  return (
    <div className="flex h-full flex-col" data-testid="checklist-runs-list">
      <div className="px-3 py-2 text-xs uppercase tracking-wide text-muted-foreground">
        In-progress runs
      </div>
      <ScrollArea className="flex-1">
        {isLoading && (
          <div className="px-3 py-2 text-sm text-muted-foreground">Loading…</div>
        )}
        {!isLoading && runs.length === 0 && (
          <div className="px-3 py-2 text-sm text-muted-foreground italic">
            No runs yet — start one from the catalogue.
          </div>
        )}
        <ul className="space-y-1 p-2">
          {runs.map((run: ChecklistRunSummary) => (
            <li
              key={run.id}
              role="button"
              tabIndex={0}
              onClick={() => onSelect(run.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  onSelect(run.id)
                }
              }}
              className={`group flex cursor-pointer items-center justify-between rounded-md px-2 py-2 text-sm hover:bg-muted ${
                run.id === activeRunId ? 'bg-muted' : ''
              }`}
              data-testid={`checklist-run-card-${run.id}`}
            >
              <div className="min-w-0">
                <div className="truncate font-medium">{run.title}</div>
                <div className="truncate text-xs text-muted-foreground">
                  {run.checklist_key.replace(/_/g, ' ')} · {run.item_count} items ·
                  {' '}
                  {run.overall_compliance_pct.toFixed(0)}% compliance
                </div>
              </div>
              <Button
                size="sm"
                variant="ghost"
                className="opacity-0 group-hover:opacity-100"
                aria-label={`Delete ${run.title}`}
                onClick={(e) => onDelete(e, run.id)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </li>
          ))}
        </ul>
      </ScrollArea>
    </div>
  )
}
