import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useImportFromMetadata } from '@/hooks/useIngest'
import { type ArticleMetadata } from '@/lib/api'

export function ImportPreviewDialog({
  projectId,
  open,
  items,
  onOpenChange,
}: {
  projectId: string
  open: boolean
  items: ArticleMetadata[]
  onOpenChange: (open: boolean) => void
}) {
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const importer = useImportFromMetadata(projectId)

  useEffect(() => {
    setSelected(new Set(items.map((_, i) => i)))
  }, [items])

  function toggle(i: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  async function onConfirm() {
    const chosen = items.filter((_, i) => selected.has(i))
    if (chosen.length === 0) {
      toast.error('Select at least one article')
      return
    }
    try {
      const resp = await importer.mutateAsync(chosen)
      const groupNote = resp.duplicate_groups.length
        ? ` · ${resp.duplicate_groups.length} duplicate group${
            resp.duplicate_groups.length === 1 ? '' : 's'
          } flagged`
        : ''
      toast.success(
        `Added ${resp.created.length} · skipped ${resp.skipped_duplicates.length} duplicate${
          resp.skipped_duplicates.length === 1 ? '' : 's'
        }${groupNote}`,
      )
      onOpenChange(false)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Import failed')
    }
  }

  const chosenCount = selected.size

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Confirm import</DialogTitle>
          <DialogDescription>
            Review the {items.length} record{items.length === 1 ? '' : 's'} below
            and pick which to add to this project's library.
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="max-h-[55vh] pr-2">
          <ul className="space-y-2">
            {items.map((m, i) => (
              <li
                key={`${m.doi ?? m.pmid ?? m.title}-${i}`}
                className="rounded-md border border-border bg-white px-3 py-2.5"
              >
                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={selected.has(i)}
                    onChange={() => toggle(i)}
                    aria-label={`Include ${m.title}`}
                  />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="secondary" className="uppercase">
                        {m.source}
                      </Badge>
                      {m.year ? (
                        <span className="text-[12px] text-muted-foreground">
                          {m.year}
                        </span>
                      ) : null}
                      {m.doi ? (
                        <span className="text-[11px] font-mono text-muted-foreground truncate">
                          DOI {m.doi}
                        </span>
                      ) : null}
                      {m.pmid ? (
                        <span className="text-[11px] font-mono text-muted-foreground">
                          PMID {m.pmid}
                        </span>
                      ) : null}
                    </div>
                    <div className="mt-1 font-medium text-[14px] line-clamp-2">
                      {m.title}
                    </div>
                    <div className="text-[12px] text-muted-foreground line-clamp-1">
                      {m.authors.length > 0 ? m.authors.join(', ') : '—'}
                      {m.journal ? ` · ${m.journal}` : ''}
                    </div>
                  </div>
                </label>
              </li>
            ))}
          </ul>
        </ScrollArea>
        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            disabled={importer.isPending}
          >
            Cancel
          </Button>
          <Button
            onClick={() => void onConfirm()}
            disabled={importer.isPending || chosenCount === 0}
          >
            {importer.isPending
              ? 'Importing…'
              : `Import ${chosenCount} article${chosenCount === 1 ? '' : 's'}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
