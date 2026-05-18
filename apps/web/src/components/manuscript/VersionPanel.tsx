/**
 * Phase 11 — Right-rail version snapshot panel.
 *
 * Lists snapshots newest-first with a "Diff" button per row, plus a
 * "New snapshot" button that opens a label/description dialog. Diffing
 * against the live state opens `VersionDiffView` inline below the row.
 */
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
import {
  useCreateSnapshot,
  useDeleteSnapshot,
  useSnapshotDiff,
  useSnapshots,
} from '@/hooks/useSnapshots'

import { VersionDiffView } from './VersionDiffView'

export function VersionPanel({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(true)
  const { data: snapshots = [], isLoading } = useSnapshots(projectId)
  const create = useCreateSnapshot(projectId)
  const remove = useDeleteSnapshot(projectId)
  const [createOpen, setCreateOpen] = useState(false)
  const [label, setLabel] = useState('')
  const [description, setDescription] = useState('')
  const [activeBaseId, setActiveBaseId] = useState<string | null>(null)
  const diffQ = useSnapshotDiff(projectId, activeBaseId, null)

  function reset() {
    setLabel('')
    setDescription('')
  }

  async function handleCreate() {
    const trimmed = label.trim()
    if (!trimmed) {
      toast.error('Label is required')
      return
    }
    try {
      await create.mutateAsync({
        label: trimmed,
        description: description.trim() || null,
      })
      toast.success(`Snapshot "${trimmed}" created`)
      setCreateOpen(false)
      reset()
    } catch (e: unknown) {
      const msg =
        e instanceof Error && /409|already/i.test(e.message)
          ? 'A snapshot with that label already exists'
          : (e as Error).message || 'Could not create snapshot'
      toast.error(msg)
    }
  }

  return (
    <Card data-testid="version-panel">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <button
            type="button"
            className="text-left"
            onClick={() => setOpen((v) => !v)}
            data-testid="version-panel-toggle"
          >
            <CardTitle className="text-[13px] font-medium">
              Versions {open ? '▾' : '▸'}
            </CardTitle>
          </button>
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button
                size="sm"
                variant="outline"
                className="h-7 px-2 text-[12px]"
                data-testid="version-panel-new"
              >
                New
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>New snapshot</DialogTitle>
                <DialogDescription>
                  Capture the manuscript&apos;s current state. Immutable — you
                  can diff or delete it later.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-3">
                <div>
                  <Label htmlFor="snapshot-label">Label</Label>
                  <Input
                    id="snapshot-label"
                    value={label}
                    placeholder="v1 – initial submission"
                    onChange={(e) => setLabel(e.target.value)}
                    data-testid="snapshot-label-input"
                  />
                </div>
                <div>
                  <Label htmlFor="snapshot-description">
                    Description (optional)
                  </Label>
                  <Textarea
                    id="snapshot-description"
                    value={description}
                    placeholder="Pre-review draft"
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  variant="ghost"
                  onClick={() => {
                    setCreateOpen(false)
                    reset()
                  }}
                >
                  Cancel
                </Button>
                <Button
                  disabled={create.isPending}
                  onClick={handleCreate}
                  data-testid="snapshot-create-confirm"
                >
                  Create
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
        <CardDescription className="text-[11px]">
          Point-in-time snapshots of every section + front-matter.
        </CardDescription>
      </CardHeader>
      {open && (
        <CardContent className="pt-0">
          {isLoading ? (
            <div className="text-[12px] text-muted-foreground">Loading…</div>
          ) : snapshots.length === 0 ? (
            <div className="text-[12px] text-muted-foreground">
              No snapshots yet.
            </div>
          ) : (
            <ScrollArea className="max-h-[320px]">
              <ul className="space-y-2">
                {snapshots.map((s) => {
                  const active = activeBaseId === s.id
                  return (
                    <li
                      key={s.id}
                      className="rounded border border-border bg-white p-2"
                      data-testid={`snapshot-row-${s.id}`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <div className="text-[12px] font-medium truncate">
                            {s.label}
                          </div>
                          {s.description ? (
                            <div className="text-[11px] text-muted-foreground line-clamp-2">
                              {s.description}
                            </div>
                          ) : null}
                          <div className="text-[10px] text-muted-foreground mt-0.5">
                            {new Date(s.created_at).toLocaleString()}
                          </div>
                        </div>
                        <div className="flex flex-col gap-1">
                          <Button
                            size="sm"
                            variant={active ? 'default' : 'outline'}
                            className="h-6 px-2 text-[11px]"
                            onClick={() =>
                              setActiveBaseId(active ? null : s.id)
                            }
                            data-testid={`snapshot-diff-${s.id}`}
                          >
                            {active ? 'Hide' : 'Diff'}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 px-2 text-[11px] text-rose-600"
                            onClick={async () => {
                              try {
                                await remove.mutateAsync(s.id)
                                if (active) setActiveBaseId(null)
                                toast.success('Snapshot deleted')
                              } catch {
                                toast.error('Could not delete')
                              }
                            }}
                            data-testid={`snapshot-delete-${s.id}`}
                          >
                            Delete
                          </Button>
                        </div>
                      </div>
                      {active ? (
                        <div className="mt-2 border-t border-border pt-2 max-h-[260px] overflow-y-auto">
                          <VersionDiffView
                            diff={diffQ.data}
                            loading={diffQ.isLoading}
                          />
                        </div>
                      ) : null}
                    </li>
                  )
                })}
              </ul>
            </ScrollArea>
          )}
        </CardContent>
      )}
    </Card>
  )
}
