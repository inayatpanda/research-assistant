import { ExternalLink, Eye, Plus, Search } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useImportFromMetadata, useSearchPubMed } from '@/hooks/useIngest'
import {
  type ArticleMetadata,
  type PubMedSearchFilters,
} from '@/lib/api'
import { cn } from '@/lib/utils'

const ARTICLE_TYPE_CHOICES = [
  'Clinical Trial',
  'Randomized Controlled Trial',
  'Review',
  'Meta-Analysis',
  'Systematic Review',
]

export function PubMedSearchDialog({ projectId }: { projectId: string }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [retmax, setRetmax] = useState(50)
  const [sort, setSort] = useState<'relevance' | 'date'>('relevance')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set())
  const [englishOnly, setEnglishOnly] = useState(false)

  const [results, setResults] = useState<ArticleMetadata[] | null>(null)
  const [previewIdx, setPreviewIdx] = useState<number | null>(null)
  const [picked, setPicked] = useState<Set<number>>(new Set())

  const search = useSearchPubMed(projectId)
  const importer = useImportFromMetadata(projectId)

  function buildFilters(): PubMedSearchFilters | undefined {
    const f: PubMedSearchFilters = {}
    if (dateFrom) f.date_from = dateFrom
    if (dateTo) f.date_to = dateTo
    if (selectedTypes.size > 0) f.article_types = Array.from(selectedTypes)
    if (englishOnly) f.english_only = true
    return Object.keys(f).length > 0 ? f : undefined
  }

  async function onSearch() {
    const q = query.trim()
    if (!q) return
    try {
      const items = await search.mutateAsync({
        query: q,
        retmax,
        sort,
        filters: buildFilters(),
      })
      if (items.length === 0) {
        toast.info('No PubMed results for that query')
        return
      }
      setResults(items)
      setPreviewIdx(null)
      setPicked(new Set(items.map((_, i) => i)))
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'PubMed search failed')
    }
  }

  function toggleType(t: string) {
    setSelectedTypes((prev) => {
      const next = new Set(prev)
      if (next.has(t)) next.delete(t)
      else next.add(t)
      return next
    })
  }

  function togglePick(i: number) {
    setPicked((prev) => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  async function onImport() {
    if (!results) return
    const chosen = results.filter((_, i) => picked.has(i))
    if (chosen.length === 0) {
      toast.error('Select at least one article')
      return
    }
    try {
      const resp = await importer.mutateAsync(chosen)
      const dupNote = resp.duplicate_groups.length
        ? ` · ${resp.duplicate_groups.length} duplicate group${resp.duplicate_groups.length === 1 ? '' : 's'} flagged`
        : ''
      toast.success(
        `Added ${resp.created.length} · skipped ${resp.skipped_duplicates.length} duplicate${resp.skipped_duplicates.length === 1 ? '' : 's'}${dupNote}`,
      )
      setOpen(false)
      setResults(null)
      setPreviewIdx(null)
      setPicked(new Set())
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Import failed')
    }
  }

  const previewItem =
    results !== null && previewIdx !== null ? results[previewIdx] : null

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o)
        if (!o) {
          setResults(null)
          setPreviewIdx(null)
        }
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline">
          <Search className="h-4 w-4 mr-1" />
          Search PubMed
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle>Search PubMed</DialogTitle>
          <DialogDescription>
            Query the NCBI E-utilities. Sort by relevance (default) or by date.
            Filter by date range, article type, or language. Click a row's
            preview button for the full abstract, MeSH terms, and affiliations.
          </DialogDescription>
        </DialogHeader>

        {/* Query / sort / retmax */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_auto] gap-2 items-end">
          <div>
            <Label htmlFor="pubmed-q">Query</Label>
            <Input
              id="pubmed-q"
              placeholder="e.g. anterior approach total hip arthroplasty"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  void onSearch()
                }
              }}
              disabled={search.isPending}
            />
          </div>
          <div className="min-w-[140px]">
            <Label htmlFor="pubmed-sort">Sort by</Label>
            <Select
              value={sort}
              onValueChange={(v) => setSort(v as 'relevance' | 'date')}
            >
              <SelectTrigger id="pubmed-sort">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="relevance">Relevance</SelectItem>
                <SelectItem value="date">Date</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="min-w-[120px]">
            <Label htmlFor="pubmed-retmax">Max results</Label>
            <Select
              value={String(retmax)}
              onValueChange={(v) => setRetmax(Number(v))}
            >
              <SelectTrigger id="pubmed-retmax">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10</SelectItem>
                <SelectItem value="20">20</SelectItem>
                <SelectItem value="50">50</SelectItem>
                <SelectItem value="100">100</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Filters */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 rounded-md border border-border p-3 bg-zinc-50/40">
          <div>
            <Label className="text-[11px] uppercase tracking-wider text-muted-foreground">
              Date range
            </Label>
            <div className="mt-1 flex items-center gap-2">
              <Input
                type="text"
                placeholder="YYYY or YYYY/MM/DD"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                aria-label="From date"
              />
              <span className="text-[12px] text-muted-foreground">–</span>
              <Input
                type="text"
                placeholder="YYYY or YYYY/MM/DD"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                aria-label="To date"
              />
            </div>
          </div>
          <div>
            <Label className="text-[11px] uppercase tracking-wider text-muted-foreground">
              Article types
            </Label>
            <div className="mt-1 flex flex-wrap gap-1.5">
              {ARTICLE_TYPE_CHOICES.map((t) => {
                const on = selectedTypes.has(t)
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => toggleType(t)}
                    aria-pressed={on}
                    className={cn(
                      'h-6 px-2 rounded-full border text-[11px] transition-colors',
                      on
                        ? 'bg-accent text-white border-accent'
                        : 'border-border bg-white text-muted-foreground hover:text-foreground',
                    )}
                  >
                    {t}
                  </button>
                )
              })}
            </div>
            <label className="mt-2 flex items-center gap-2 text-[12px] text-muted-foreground">
              <input
                type="checkbox"
                checked={englishOnly}
                onChange={(e) => setEnglishOnly(e.target.checked)}
              />
              English only
            </label>
          </div>
        </div>

        {/* Action row */}
        <div className="flex items-center justify-between gap-2">
          <Button
            onClick={() => void onSearch()}
            disabled={search.isPending || !query.trim()}
          >
            {search.isPending ? 'Searching…' : 'Search'}
          </Button>
          {results !== null && (
            <Button
              onClick={() => void onImport()}
              disabled={importer.isPending || picked.size === 0}
            >
              {importer.isPending
                ? 'Importing…'
                : `Import ${picked.size} article${picked.size === 1 ? '' : 's'}`}
            </Button>
          )}
        </div>

        {/* Split results / preview */}
        {results !== null && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3" data-testid="pubmed-results-pane">
            <ScrollArea className="max-h-[420px] pr-2 rounded-md border border-border bg-white">
              <ul className="p-2 space-y-1">
                {results.map((m, i) => (
                  <li
                    key={`${m.pmid ?? m.doi ?? m.title}-${i}`}
                    className={cn(
                      'rounded-md border bg-white px-2.5 py-2 text-[12px]',
                      previewIdx === i
                        ? 'border-accent ring-1 ring-accent/30'
                        : 'border-border',
                    )}
                  >
                    <div className="flex items-start gap-2">
                      <input
                        type="checkbox"
                        className="mt-1"
                        checked={picked.has(i)}
                        onChange={() => togglePick(i)}
                        aria-label={`Include ${m.title}`}
                      />
                      <div className="min-w-0 flex-1">
                        <div className="font-medium leading-[16px] line-clamp-2">
                          {m.title}
                        </div>
                        <div className="mt-0.5 text-[11px] text-muted-foreground line-clamp-1">
                          {m.authors.slice(0, 3).join(', ')}
                          {m.authors.length > 3
                            ? ` +${m.authors.length - 3}`
                            : ''}
                          {m.journal ? ` · ${m.journal}` : ''}
                          {m.year ? ` · ${m.year}` : ''}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => setPreviewIdx(i)}
                        aria-label="Preview"
                        className="text-muted-foreground hover:text-foreground p-1 rounded hover:bg-muted shrink-0"
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            </ScrollArea>

            <div
              data-testid="pubmed-preview-pane"
              className="max-h-[420px] overflow-y-auto rounded-md border border-border bg-white p-4"
            >
              {previewItem ? (
                <article className="space-y-3">
                  <header className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap text-[11px] text-muted-foreground">
                      {previewItem.year ? <span>{previewItem.year}</span> : null}
                      {previewItem.journal ? (
                        <span>· {previewItem.journal}</span>
                      ) : null}
                      {previewItem.pmid ? (
                        <span className="font-mono">· PMID {previewItem.pmid}</span>
                      ) : null}
                    </div>
                    <h3 className="text-[14px] font-semibold tracking-tight">
                      {previewItem.title}
                    </h3>
                    {previewItem.authors.length > 0 && (
                      <div className="text-[12px] text-muted-foreground">
                        {previewItem.authors.join(', ')}
                      </div>
                    )}
                  </header>

                  {previewItem.article_types &&
                    previewItem.article_types.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {previewItem.article_types.map((t) => (
                          <Badge
                            key={t}
                            variant="outline"
                            className="text-[10px] uppercase tracking-wider"
                          >
                            {t}
                          </Badge>
                        ))}
                      </div>
                    )}

                  {previewItem.abstract && (
                    <section>
                      <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-1">
                        Abstract
                      </div>
                      <p className="text-[12px] leading-[18px] whitespace-pre-wrap">
                        {previewItem.abstract}
                      </p>
                    </section>
                  )}

                  {previewItem.mesh_terms && previewItem.mesh_terms.length > 0 && (
                    <section>
                      <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-1">
                        MeSH terms
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {previewItem.mesh_terms.map((m) => (
                          <span
                            key={m}
                            className="text-[11px] px-1.5 py-0.5 rounded-full bg-zinc-100 text-zinc-700"
                          >
                            {m}
                          </span>
                        ))}
                      </div>
                    </section>
                  )}

                  {previewItem.affiliations &&
                    previewItem.affiliations.length > 0 && (
                      <section>
                        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-1">
                          Affiliations
                        </div>
                        <ul className="space-y-1">
                          {previewItem.affiliations.map((a, i) => (
                            <li key={i} className="text-[11px] text-muted-foreground">
                              {a}
                            </li>
                          ))}
                        </ul>
                      </section>
                    )}

                  <div className="flex items-center justify-between pt-2 border-t border-border">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        if (previewIdx !== null) togglePick(previewIdx)
                      }}
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      {previewIdx !== null && picked.has(previewIdx)
                        ? 'Unselect'
                        : 'Select for import'}
                    </Button>
                    {previewItem.pmid && (
                      <a
                        href={`https://pubmed.ncbi.nlm.nih.gov/${previewItem.pmid}/`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[12px] text-accent hover:underline inline-flex items-center gap-1"
                      >
                        View on PubMed
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                </article>
              ) : (
                <div className="h-full flex items-center justify-center text-center text-[12px] text-muted-foreground">
                  Pick a result to preview its abstract, MeSH terms, and
                  affiliations.
                </div>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
