/**
 * MeSH Browser (MP19) — searchable input → list of MeSH descriptors.
 * Each row exposes a "Pin to cache" button that calls the cache upsert
 * endpoint so subsequent runs can resolve the descriptor offline.
 */
import { Loader2, Pin, Search, X } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { MeshSearchHit } from '@/lib/api'
import {
  useDeleteMesh,
  useMeshCache,
  useMeshSearch,
  useUpsertMesh,
} from '@/hooks/useMesh'

type Props = {
  projectId: string
  onAddToQuery?: (hit: MeshSearchHit) => void
}

export function MeSHBrowser({ projectId, onAddToQuery }: Props) {
  const [draft, setDraft] = useState('')
  const [query, setQuery] = useState('')
  const search = useMeshSearch(projectId, query, !!query)
  const cache = useMeshCache(projectId)
  const upsert = useUpsertMesh(projectId)
  const remove = useDeleteMesh(projectId)

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    setQuery(draft.trim())
  }

  const pin = async (h: MeshSearchHit) => {
    try {
      await upsert.mutateAsync({
        descriptor_ui: h.descriptor_ui,
        descriptor_name: h.descriptor_name,
        scope_note: h.scope_note ?? null,
        tree_numbers: h.tree_numbers,
        entry_terms: h.entry_terms,
        source: 'ncbi_lookup',
      })
      toast.success('Pinned to MeSH cache.')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Pin failed.')
    }
  }

  return (
    <div className="space-y-6" data-testid="mesh-browser">
      <form onSubmit={submit} className="flex gap-2 max-w-2xl">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Search MeSH (e.g. hip arthroplasty)"
            className="pl-9"
            data-testid="mesh-search-input"
          />
        </div>
        <Button type="submit" disabled={!draft.trim() || search.isFetching}>
          {search.isFetching ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            'Search'
          )}
        </Button>
      </form>

      {search.isError && (
        <div className="text-sm text-destructive">
          MeSH search failed: {(search.error as Error)?.message}
        </div>
      )}

      {search.data && (
        <section data-testid="mesh-search-results">
          <h3 className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-2">
            Results ({search.data.hits.length})
          </h3>
          <div className="space-y-2">
            {search.data.hits.length === 0 && (
              <div className="text-sm text-muted-foreground">
                No descriptors found.
              </div>
            )}
            {search.data.hits.map((h) => (
              <article
                key={h.descriptor_ui}
                className="rounded-md border border-border bg-card px-4 py-3"
                data-testid={`mesh-hit-${h.descriptor_ui}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-medium">{h.descriptor_name}</div>
                    <div className="text-xs text-muted-foreground">
                      UI: <code>{h.descriptor_ui}</code>
                      {h.tree_numbers.length > 0 && (
                        <> · Tree: {h.tree_numbers.join(', ')}</>
                      )}
                    </div>
                    {h.scope_note && (
                      <p className="mt-2 text-sm text-muted-foreground">
                        {h.scope_note}
                      </p>
                    )}
                    {h.entry_terms.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {h.entry_terms.slice(0, 8).map((t) => (
                          <span
                            key={t}
                            className="rounded bg-muted px-1.5 py-0.5 text-[11px]"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 shrink-0">
                    {onAddToQuery && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onAddToQuery(h)}
                      >
                        Add to query
                      </Button>
                    )}
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => pin(h)}
                    >
                      <Pin className="h-3.5 w-3.5 mr-1" />
                      Pin
                    </Button>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {cache.data && cache.data.length > 0 && (
        <section>
          <h3 className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-2">
            Pinned cache ({cache.data.length})
          </h3>
          <div className="space-y-1.5">
            {cache.data.map((row) => (
              <div
                key={row.id}
                className="flex items-center justify-between gap-2 rounded border border-border px-3 py-1.5 text-sm"
              >
                <div className="truncate">
                  <span className="font-medium">{row.descriptor_name}</span>
                  <span className="ml-2 text-xs text-muted-foreground">
                    {row.descriptor_ui}
                  </span>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => remove.mutate(row.id)}
                  title="Remove from cache"
                >
                  <X className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
