/**
 * PublicationBiasPanel (MP19) — runs all 4 publication-bias tests
 * (Egger / Begg / Harbord / Peters) for a meta-analysis and shows pass/fail
 * badges plus the asymptotic p-value.
 */
import { Loader2 } from 'lucide-react'

import { usePublicationBias } from '@/hooks/useMetaExtensions'

type Props = {
  projectId: string
  metaId: string
}

const SIGNIFICANT = 0.05

export function PublicationBiasPanel({ projectId, metaId }: Props) {
  const q = usePublicationBias(projectId, metaId)

  if (q.isLoading)
    return <Loader2 className="h-4 w-4 animate-spin" data-testid="pb-loading" />
  if (q.isError)
    return (
      <div className="text-sm text-destructive">
        Publication-bias test failed: {(q.error as Error).message}
      </div>
    )
  if (!q.data) return null

  return (
    <section data-testid="publication-bias-panel" className="space-y-3">
      <header>
        <h3 className="text-sm font-medium">Publication-bias tests</h3>
        <p className="text-[12px] text-muted-foreground">
          k = {q.data.k} studies · recommended:{' '}
          <code>{q.data.recommended}</code>
        </p>
      </header>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-wide text-muted-foreground border-b border-border">
            <th className="py-1.5">Test</th>
            <th className="py-1.5">Statistic</th>
            <th className="py-1.5">p</th>
            <th className="py-1.5">Verdict</th>
            <th className="py-1.5">Note</th>
          </tr>
        </thead>
        <tbody>
          {q.data.tests.map((t) => {
            const sig = t.p != null && t.p < SIGNIFICANT
            return (
              <tr
                key={t.method}
                className="border-b border-border/40"
                data-testid={`pb-row-${t.method}`}
              >
                <td className="py-1.5 capitalize">{t.method}</td>
                <td className="py-1.5">
                  {t.statistic == null
                    ? '—'
                    : t.statistic.toFixed(3)}
                </td>
                <td className="py-1.5">
                  {t.p == null ? '—' : t.p.toFixed(3)}
                </td>
                <td className="py-1.5">
                  {t.p == null ? (
                    <span className="text-muted-foreground">n/a</span>
                  ) : sig ? (
                    <span
                      className="rounded bg-amber-100 dark:bg-amber-900/40 px-1.5 py-0.5 text-[10px] text-amber-900 dark:text-amber-200"
                      data-testid={`pb-verdict-${t.method}`}
                    >
                      possible bias
                    </span>
                  ) : (
                    <span
                      className="rounded bg-emerald-100 dark:bg-emerald-900/40 px-1.5 py-0.5 text-[10px] text-emerald-900 dark:text-emerald-200"
                      data-testid={`pb-verdict-${t.method}`}
                    >
                      no asymmetry
                    </span>
                  )}
                </td>
                <td className="py-1.5 text-[12px] text-muted-foreground">
                  {t.note ?? ''}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </section>
  )
}
