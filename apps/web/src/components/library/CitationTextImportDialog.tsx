/**
 * Phase 16 (MP16) — Bulk-paste citation text → preview → confirm.
 *
 * Two-step UX:
 *   1. Paste multiline citations into the textarea, hit "Parse" → calls
 *      ``POST /articles/import-from-text`` which returns a preview list.
 *   2. The user toggles which ``status='ok'`` rows to keep, then "Confirm"
 *      bulk-adds them via the existing ``import-from-metadata`` route.
 */
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
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
import {
  citationImportApi,
  type ParsedReferencePreview,
} from '@/lib/api'
import { useImportFromMetadata } from '@/hooks/useIngest'

export function CitationTextImportDialog({
  projectId,
  open,
  onOpenChange,
}: {
  projectId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [text, setText] = useState('')
  const [parsing, setParsing] = useState(false)
  const [items, setItems] = useState<ParsedReferencePreview[]>([])
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const importer = useImportFromMetadata(projectId)

  function reset() {
    setText('')
    setItems([])
    setSelected(new Set())
  }

  async function onParse() {
    if (!text.trim()) {
      toast.error('Paste at least one reference')
      return
    }
    setParsing(true)
    try {
      const resp = await citationImportApi.importFromText(projectId, text)
      setItems(resp.items)
      // Pre-select all resolved entries; unresolved must be checked manually.
      setSelected(
        new Set(
          resp.items
            .map((r, i) => (r.status === 'ok' ? i : -1))
            .filter((i) => i >= 0),
        ),
      )
      const okCount = resp.items.filter((r) => r.status === 'ok').length
      toast.success(
        `Parsed ${resp.items.length} reference${resp.items.length === 1 ? '' : 's'} · ${okCount} resolved`,
      )
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Parse failed')
    } finally {
      setParsing(false)
    }
  }

  function toggle(i: number) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  async function onConfirm() {
    const chosen = items
      .filter((_, i) => selected.has(i))
      .map((r) => r.parsed_metadata)
      .filter((m): m is NonNullable<typeof m> => m != null)
    if (chosen.length === 0) {
      toast.error('Select at least one resolved entry')
      return
    }
    try {
      const resp = await importer.mutateAsync(chosen)
      toast.success(
        `Added ${resp.created.length} · skipped ${resp.skipped_duplicates.length} duplicate${
          resp.skipped_duplicates.length === 1 ? '' : 's'
        }`,
      )
      reset()
      onOpenChange(false)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Import failed')
    }
  }

  const okCount = items.filter((r) => r.status === 'ok').length
  const chosenCount = selected.size

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Paste citation text</DialogTitle>
          <DialogDescription>
            Paste a list of references (Vancouver-numbered, blank-line
            separated, or one per line). DOIs and PMIDs are resolved via
            Crossref / PubMed; entries without identifiers fall back to a
            high-confidence Crossref title search.
          </DialogDescription>
        </DialogHeader>

        {items.length === 0 ? (
          <div className="space-y-2">
            <textarea
              data-testid="citation-text-input"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder={
                '1. Doe J, Smith K. Title. J Foo 2024;1:1-5. doi:10.1234/abc\n2. Patel R. Another. PMID: 12345678\n3. ...'
              }
              className="w-full min-h-[200px] rounded-md border border-border bg-white px-3 py-2 text-[12px] font-mono"
              aria-label="Citation text"
            />
          </div>
        ) : (
          <ScrollArea className="max-h-[55vh] pr-2">
            <ul className="space-y-2">
              {items.map((r, i) => {
                const meta = r.parsed_metadata
                const isOk = r.status === 'ok'
                return (
                  <li
                    key={i}
                    className="rounded-md border border-border bg-white px-3 py-2.5"
                  >
                    <label className="flex items-start gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={selected.has(i)}
                        onChange={() => toggle(i)}
                        disabled={!isOk}
                        aria-label={`Include reference ${i + 1}`}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge
                            variant={isOk ? 'secondary' : 'outline'}
                            className="uppercase"
                          >
                            {r.status}
                          </Badge>
                          {r.doi ? (
                            <span className="text-[10px] font-mono text-muted-foreground">
                              doi:{r.doi}
                            </span>
                          ) : null}
                          {r.pmid ? (
                            <span className="text-[10px] font-mono text-muted-foreground">
                              PMID:{r.pmid}
                            </span>
                          ) : null}
                        </div>
                        {meta ? (
                          <>
                            <div className="text-[13px] font-medium mt-1">
                              {meta.title}
                            </div>
                            <div className="text-[11px] text-muted-foreground">
                              {meta.authors.slice(0, 3).join(', ')}
                              {meta.authors.length > 3 ? ', et al.' : ''}
                              {meta.year ? ` · ${meta.year}` : ''}
                              {meta.journal ? ` · ${meta.journal}` : ''}
                            </div>
                          </>
                        ) : (
                          <div className="text-[12px] text-muted-foreground mt-1 italic">
                            {r.raw.slice(0, 200)}
                            {r.raw.length > 200 ? '…' : ''}
                          </div>
                        )}
                        {r.notes.length > 0 ? (
                          <div className="text-[10px] text-amber-700 mt-1">
                            {r.notes.join(' · ')}
                          </div>
                        ) : null}
                      </div>
                    </label>
                  </li>
                )
              })}
            </ul>
          </ScrollArea>
        )}

        <DialogFooter className="flex items-center justify-between sm:justify-between gap-2">
          {items.length > 0 ? (
            <div className="text-[11px] text-muted-foreground mr-auto">
              {okCount} of {items.length} resolved · {chosenCount} selected
            </div>
          ) : null}
          {items.length === 0 ? (
            <Button onClick={onParse} disabled={parsing || !text.trim()}>
              {parsing ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                  Parsing…
                </>
              ) : (
                'Parse'
              )}
            </Button>
          ) : (
            <div className="flex gap-2">
              <Button variant="outline" onClick={reset}>
                Back
              </Button>
              <Button
                onClick={onConfirm}
                disabled={chosenCount === 0 || importer.isPending}
              >
                {importer.isPending ? 'Adding…' : `Add ${chosenCount}`}
              </Button>
            </div>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
