/**
 * LeaveOneOutTable (MP19) — sortable table of per-excluded-study pooled
 * effect + 95% CI + I². Inline mini-sparkline using a simple svg.
 */
import { Loader2 } from 'lucide-react'

import { useLeaveOneOut } from '@/hooks/useMetaExtensions'

type Props = {
  projectId: string
  metaId: string
}

export function LeaveOneOutTable({ projectId, metaId }: Props) {
  const q = useLeaveOneOut(projectId, metaId)

  if (q.isLoading)
    return <Loader2 className="h-4 w-4 animate-spin" data-testid="loo-loading" />
  if (q.isError)
    return (
      <div className="text-sm text-destructive">
        Leave-one-out failed: {(q.error as Error).message}
      </div>
    )
  if (!q.data) return null

  const effects = q.data.rows.map((r) => r.pooled_effect)
  const min = Math.min(...effects)
  const max = Math.max(...effects)
  const range = max - min || 1

  return (
    <section data-testid="leave-one-out-table" className="space-y-2">
      <header className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Leave-one-out sensitivity</h3>
        <span className="text-[11px] text-muted-foreground">
          k = {q.data.k} · {q.data.model} effects
        </span>
      </header>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-wide text-muted-foreground border-b border-border">
            <th className="py-1.5">Excluded</th>
            <th className="py-1.5">Pooled</th>
            <th className="py-1.5">95% CI</th>
            <th className="py-1.5">I²</th>
            <th className="py-1.5 w-32">Δ effect</th>
          </tr>
        </thead>
        <tbody>
          {q.data.rows.map((r) => {
            const norm = (r.pooled_effect - min) / range
            return (
              <tr
                key={r.excluded_id}
                className="border-b border-border/40"
                data-testid={`loo-row-${r.excluded_id}`}
              >
                <td className="py-1.5 font-medium">−{r.excluded_id}</td>
                <td className="py-1.5">{r.pooled_effect.toFixed(3)}</td>
                <td className="py-1.5 text-[12px] text-muted-foreground">
                  [{r.ci_low.toFixed(3)}, {r.ci_high.toFixed(3)}]
                </td>
                <td className="py-1.5">{r.i2.toFixed(1)}%</td>
                <td className="py-1.5">
                  <div className="relative h-2 rounded bg-muted overflow-hidden">
                    <div
                      className="absolute inset-y-0 left-0 bg-accent"
                      style={{ width: `${(norm * 100).toFixed(1)}%` }}
                    />
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </section>
  )
}
