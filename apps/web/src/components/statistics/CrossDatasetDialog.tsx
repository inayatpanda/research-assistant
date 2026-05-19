import { Combine, Loader2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  crossDatasetApi,
  type CrossOpName,
  type CrossOpRequest,
  type Dataset,
} from '@/lib/api'

const HOW_MERGE = ['inner', 'left', 'right', 'outer'] as const
const HOW_JOIN = ['left', 'right', 'inner', 'outer'] as const

export function CrossDatasetDialog({
  open,
  onOpenChange,
  projectId,
  datasets,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: string
  datasets: Dataset[]
}) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [op, setOp] = useState<CrossOpName>('merge')
  const [sourceIds, setSourceIds] = useState<string[]>([])
  const [mergeKeys, setMergeKeys] = useState<string>('')
  const [joinKey, setJoinKey] = useState<string>('')
  const [how, setHow] = useState<string>('inner')

  useEffect(() => {
    if (open) {
      setOp('merge')
      setSourceIds([])
      setMergeKeys('')
      setJoinKey('')
      setHow('inner')
    }
  }, [open])

  const mutation = useMutation({
    mutationFn: (body: CrossOpRequest) =>
      crossDatasetApi.crossOp(projectId, body),
  })

  const requiredCount = op === 'append' ? 0 : 2 // append: >= 2 (any), merge/join: exactly 2
  const eligible = useMemo(() => datasets, [datasets])

  function toggle(id: string) {
    setSourceIds((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id)
      if (op !== 'append' && prev.length >= 2) return [prev[1], id]
      return [...prev, id]
    })
  }

  function onSubmit() {
    if (op === 'append') {
      if (sourceIds.length < 2) {
        toast.error('Pick at least 2 datasets to append')
        return
      }
    } else if (sourceIds.length !== 2) {
      toast.error('Pick exactly 2 datasets')
      return
    }

    const args: Record<string, unknown> = {}
    if (op === 'merge') {
      const keys = mergeKeys
        .split(',')
        .map((s) => s.trim())
        .filter((s) => s.length > 0)
      if (keys.length === 0) {
        toast.error('Provide at least one merge key column')
        return
      }
      args.on = keys
      args.how = how
    } else if (op === 'join') {
      if (!joinKey.trim()) {
        toast.error('Provide a join key column')
        return
      }
      args.on = joinKey.trim()
      args.how = how
    }

    mutation.mutate(
      { op, source_dataset_ids: sourceIds, args },
      {
        onSuccess: (resp) => {
          qc.invalidateQueries({ queryKey: ['datasets', projectId] })
          toast.success(`Created ${resp.filename} (${resp.n_rows} rows)`)
          onOpenChange(false)
          navigate(
            `/projects/${projectId}/statistics?dataset=${resp.dataset_id}`,
          )
        },
        onError: (e: Error) => toast.error(e.message),
      },
    )
  }

  const howOptions = op === 'merge' ? HOW_MERGE : HOW_JOIN

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Cross-dataset operation</DialogTitle>
          <DialogDescription>
            Combine two or more datasets into a new derived dataset.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="cross-op">Operation</Label>
            <Select
              value={op}
              onValueChange={(v) => {
                setOp(v as CrossOpName)
                setSourceIds([])
                setHow(v === 'merge' ? 'inner' : 'left')
              }}
            >
              <SelectTrigger id="cross-op">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="merge">Merge (multi-key join)</SelectItem>
                <SelectItem value="join">Join (single key)</SelectItem>
                <SelectItem value="append">Append (stack rows)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>
              Source datasets
              {op !== 'append' && (
                <span className="ml-1 text-[11px] font-normal text-muted-foreground">
                  (exactly {requiredCount})
                </span>
              )}
            </Label>
            <div className="rounded-md border border-border bg-white p-2 max-h-[200px] overflow-y-auto">
              {eligible.length === 0 ? (
                <div className="text-[12px] text-muted-foreground px-2 py-1">
                  No datasets in this project.
                </div>
              ) : (
                <ul className="space-y-0.5">
                  {eligible.map((d) => (
                    <li key={d.id}>
                      <label className="flex items-center gap-2 px-2 py-1 rounded hover:bg-muted/50 cursor-pointer text-[13px]">
                        <input
                          type="checkbox"
                          checked={sourceIds.includes(d.id)}
                          onChange={() => toggle(d.id)}
                        />
                        <span className="truncate">{d.filename}</span>
                        <span className="ml-auto text-[11px] text-muted-foreground tabular-nums">
                          {d.n_rows}×{d.n_columns}
                        </span>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {op === 'merge' && (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="cross-keys">Merge keys (comma-separated)</Label>
                <Input
                  id="cross-keys"
                  value={mergeKeys}
                  onChange={(e) => setMergeKeys(e.target.value)}
                  placeholder="patient_id, visit_id"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="cross-how">How</Label>
                <Select value={how} onValueChange={setHow}>
                  <SelectTrigger id="cross-how">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {howOptions.map((h) => (
                      <SelectItem key={h} value={h}>
                        {h}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </>
          )}

          {op === 'join' && (
            <>
              <div className="space-y-1.5">
                <Label htmlFor="cross-join-key">Join key column</Label>
                <Input
                  id="cross-join-key"
                  value={joinKey}
                  onChange={(e) => setJoinKey(e.target.value)}
                  placeholder="patient_id"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="cross-how-join">How</Label>
                <Select value={how} onValueChange={setHow}>
                  <SelectTrigger id="cross-how-join">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {howOptions.map((h) => (
                      <SelectItem key={h} value={h}>
                        {h}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            onClick={onSubmit}
            disabled={mutation.isPending}
            className="bg-accent hover:bg-accent-hover text-white"
          >
            {mutation.isPending ? (
              <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
            ) : (
              <Combine className="h-4 w-4 mr-1.5" />
            )}
            Create derived dataset
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
