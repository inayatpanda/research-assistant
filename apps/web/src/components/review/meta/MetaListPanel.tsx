import { useSearchParams } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import { useMetaList } from '@/hooks/useMeta'
import { cn } from '@/lib/utils'

import { MetaAnalysisForm } from './MetaAnalysisForm'

export function MetaListPanel({ projectId }: { projectId: string }) {
  const [params, setParams] = useSearchParams()
  const selectedId = params.get('meta')
  const { data: list = [], isLoading } = useMetaList(projectId)

  const select = (id: string) => {
    const next = new URLSearchParams(params)
    next.set('meta', id)
    setParams(next, { replace: true })
  }

  return (
    <aside className="w-72 shrink-0 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-[13px] font-semibold">Meta-analyses</h3>
        <MetaAnalysisForm projectId={projectId} onCreated={(id) => select(id)} />
      </div>
      {isLoading ? (
        <div className="text-[12px] text-muted-foreground">Loading…</div>
      ) : list.length === 0 ? (
        <div className="rounded-md border border-dashed border-border p-4 text-center text-[12px] text-muted-foreground">
          No meta-analyses yet. Create one to start pooling effects across included studies.
        </div>
      ) : (
        <ul className="space-y-1">
          {list.map((m) => (
            <li key={m.id}>
              <button
                onClick={() => select(m.id)}
                className={cn(
                  'w-full rounded-md border border-border bg-white px-3 py-2 text-left text-[12px] hover:border-accent',
                  selectedId === m.id && 'border-accent shadow-sm',
                )}
              >
                <div className="font-medium truncate">
                  {m.title || `${m.effect_metric.toUpperCase()} (${m.model})`}
                </div>
                <div className="mt-1 flex items-center gap-2 text-[11px] text-muted-foreground">
                  <Badge variant="outline" className="text-[10px]">
                    {m.effect_metric.toUpperCase()}
                  </Badge>
                  <span>k={m.inputs.length}</span>
                  <span>·</span>
                  <span>{m.status}</span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
