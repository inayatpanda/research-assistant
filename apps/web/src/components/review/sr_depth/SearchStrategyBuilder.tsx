/**
 * SearchStrategyBuilder (MP19) — composer for boolean queries with MeSH
 * chips and free-text terms. Persists per-review search strategies.
 */
import { Loader2, Plus, Save, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type {
  SearchDatabase,
  SearchStrategyRead,
} from '@/lib/api'
import {
  useCreateSearchStrategy,
  useDeleteSearchStrategy,
  useSearchStrategies,
  useUpdateSearchStrategy,
} from '@/hooks/useSearchStrategies'

const DATABASES: SearchDatabase[] = [
  'PubMed',
  'Embase',
  'Cochrane',
  'Web of Science',
  'Scopus',
  'Other',
]

const OPERATORS = ['AND', 'OR', 'NOT'] as const

export function SearchStrategyBuilder({ projectId }: { projectId: string }) {
  const list = useSearchStrategies(projectId)
  const create = useCreateSearchStrategy(projectId)
  const update = useUpdateSearchStrategy(projectId)
  const remove = useDeleteSearchStrategy(projectId)

  const [name, setName] = useState('Untitled strategy')
  const [database, setDatabase] = useState<SearchDatabase>('PubMed')
  const [query, setQuery] = useState('')

  const insert = (text: string) => setQuery((q) => (q ? `${q} ${text}` : text))

  const save = async () => {
    if (!query.trim()) {
      toast.error('Add at least one term first.')
      return
    }
    try {
      await create.mutateAsync({
        name,
        database,
        query_text: query,
        mesh_term_ids: [],
      })
      toast.success('Strategy saved.')
      setQuery('')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Save failed.')
    }
  }

  return (
    <div className="space-y-6" data-testid="search-strategy-builder">
      <section className="rounded-md border border-border bg-card p-4 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="ss-name">Name</Label>
            <Input
              id="ss-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="ss-db">Database</Label>
            <select
              id="ss-db"
              className="mt-1 w-full rounded border border-border bg-background px-2 py-1.5 text-sm"
              value={database}
              onChange={(e) => setDatabase(e.target.value as SearchDatabase)}
            >
              {DATABASES.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <Label>Query</Label>
          <Textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='e.g. "hip arthroplasty"[MeSH Terms] AND anesthesia[tw]'
            rows={4}
            data-testid="ss-query"
          />
        </div>

        <div className="flex flex-wrap gap-1.5">
          {OPERATORS.map((op) => (
            <Button
              key={op}
              size="sm"
              variant="outline"
              type="button"
              onClick={() => insert(op)}
              data-testid={`op-${op}`}
            >
              {op}
            </Button>
          ))}
          <Button
            size="sm"
            variant="outline"
            type="button"
            onClick={() => insert('()')}
          >
            ( )
          </Button>
          <Button
            size="sm"
            variant="outline"
            type="button"
            onClick={() => insert('""')}
          >
            "term"
          </Button>
        </div>

        <div>
          <Button onClick={save} disabled={create.isPending}>
            {create.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin mr-1" />
            ) : (
              <Save className="h-4 w-4 mr-1" />
            )}
            Save strategy
          </Button>
        </div>
      </section>

      <section>
        <h3 className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-2">
          Saved strategies ({list.data?.length ?? 0})
        </h3>
        {list.isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
        <div className="space-y-2">
          {(list.data ?? []).map((s) => (
            <SavedStrategyRow
              key={s.id}
              strategy={s}
              onUpdate={(body) =>
                update.mutate({ id: s.id, body })
              }
              onDelete={() => remove.mutate(s.id)}
            />
          ))}
        </div>
      </section>
    </div>
  )
}

function SavedStrategyRow({
  strategy,
  onUpdate,
  onDelete,
}: {
  strategy: SearchStrategyRead
  onUpdate: (body: Partial<{ is_locked: boolean }>) => void
  onDelete: () => void
}) {
  return (
    <article
      className="rounded border border-border bg-card px-4 py-3 text-sm"
      data-testid={`ss-row-${strategy.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="font-medium flex items-center gap-2">
            {strategy.name}
            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] uppercase tracking-wide">
              {strategy.database}
            </span>
            {strategy.is_locked && (
              <span className="rounded bg-amber-100 dark:bg-amber-900/40 px-1.5 py-0.5 text-[10px]">
                locked
              </span>
            )}
          </div>
          <pre className="mt-1 whitespace-pre-wrap break-words text-[12px] text-muted-foreground">
            {strategy.query_text}
          </pre>
          {strategy.warnings && strategy.warnings.length > 0 && (
            <div className="mt-2 text-[11px] text-amber-700 dark:text-amber-300">
              {strategy.warnings.length} translation warning(s)
            </div>
          )}
        </div>
        <div className="flex flex-col gap-1 shrink-0">
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onUpdate({ is_locked: !strategy.is_locked })}
          >
            {strategy.is_locked ? 'Unlock' : 'Lock'}
          </Button>
          <Button size="sm" variant="ghost" onClick={onDelete}>
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
    </article>
  )
}
