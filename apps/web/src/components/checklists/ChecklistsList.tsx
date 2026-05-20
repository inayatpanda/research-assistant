import { useState } from 'react'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  useChecklistCatalogue,
  useCreateChecklistRun,
} from '@/hooks/useChecklists'
import type { ChecklistCatalogueSummary, ChecklistRunRead } from '@/lib/api'

export type ChecklistsListProps = {
  projectId: string
  onRunCreated?: (run: ChecklistRunRead) => void
}

/**
 * MP20 — Left rail listing the 12 available reporting checklists. Each
 * row has a "Start" button that opens a dialog asking for a title (e.g.
 * "v1 submission to JBJS"). Submitting creates the run and notifies the
 * parent so it can navigate the user into the run drawer.
 */
export function ChecklistsList({ projectId, onRunCreated }: ChecklistsListProps) {
  const { data: catalogue = [], isLoading } = useChecklistCatalogue()
  const createMutation = useCreateChecklistRun(projectId)
  const [active, setActive] = useState<ChecklistCatalogueSummary | null>(null)
  const [title, setTitle] = useState('')
  const [error, setError] = useState<string | null>(null)

  const close = () => {
    setActive(null)
    setTitle('')
    setError(null)
  }

  const submit = async () => {
    if (!active) return
    setError(null)
    try {
      const run = await createMutation.mutateAsync({
        checklist_key: active.key,
        title: title.trim(),
      })
      close()
      onRunCreated?.(run)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create run')
    }
  }

  return (
    <div className="flex h-full flex-col" data-testid="checklists-catalogue-list">
      <div className="px-3 py-2 text-xs uppercase tracking-wide text-muted-foreground">
        Reporting checklists
      </div>
      <ScrollArea className="flex-1">
        {isLoading && (
          <div className="px-3 py-2 text-sm text-muted-foreground">Loading…</div>
        )}
        {!isLoading && catalogue.length === 0 && (
          <div className="px-3 py-2 text-sm text-muted-foreground italic">
            No catalogues found.
          </div>
        )}
        <ul className="space-y-1 p-2">
          {catalogue.map((cat) => (
            <li
              key={cat.key}
              className="flex items-center justify-between rounded-md border border-transparent px-2 py-1.5 hover:border-border hover:bg-muted"
              data-testid={`checklist-row-${cat.key}`}
            >
              <div className="min-w-0">
                <div className="truncate text-sm font-medium">{cat.name}</div>
                <div className="truncate text-xs text-muted-foreground">
                  {cat.item_count} items · {cat.version}
                </div>
              </div>
              <Button
                size="sm"
                variant="default"
                onClick={() => setActive(cat)}
                aria-label={`Start ${cat.name}`}
              >
                Start
              </Button>
            </li>
          ))}
        </ul>
      </ScrollArea>

      <Dialog open={active !== null} onOpenChange={(o) => !o && close()}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Start {active?.name}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="checklist-run-title">Run title</Label>
            <Input
              id="checklist-run-title"
              value={title}
              placeholder="e.g. v1 submission to JBJS"
              onChange={(e) => setTitle(e.target.value)}
              autoFocus
            />
            {active && (
              <p className="text-xs text-muted-foreground">
                {active.description}
              </p>
            )}
            {error && (
              <p className="text-xs text-rose-600" data-testid="checklist-create-error">
                {error}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={close}>Cancel</Button>
            <Button
              onClick={submit}
              disabled={title.trim().length === 0 || createMutation.isPending}
            >
              {createMutation.isPending ? 'Creating…' : 'Start checklist'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
