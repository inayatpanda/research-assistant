/**
 * Phase 17 (MP17) — Multiple-imputation card.
 *
 * Lets users pick a method + target columns + n_imputations + seed and
 * runs MICE (or a simple fallback). Displays the pooled per-column
 * Rubin-rule summary returned by the backend.
 */
import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'

import { imputationApi } from '../../lib/api'

interface Props {
  projectId: string
  datasetId: string
  numericColumns: string[]
}

export function ImputationCard({ projectId, datasetId, numericColumns }: Props) {
  const [method, setMethod] = useState<'mice' | 'mean' | 'median' | 'knn' | 'last_observation'>('mice')
  const [n, setN] = useState(5)
  const [seed, setSeed] = useState(42)
  const [selected, setSelected] = useState<string[]>([])

  const runMutation = useMutation({
    mutationFn: () =>
      imputationApi.run(projectId, datasetId, {
        method,
        target_cols: selected,
        n_imputations: n,
        seed,
      }),
  })

  const { data: history } = useQuery({
    queryKey: ['imputation-runs', projectId, datasetId],
    queryFn: () => imputationApi.list(projectId, datasetId),
  })

  return (
    <div data-testid="imputation-card">
      <h4>Multiple imputation</h4>
      <label>
        Method
        <select value={method} onChange={(e) => setMethod(e.target.value as never)}>
          <option value="mice">MICE</option>
          <option value="knn">KNN</option>
          <option value="mean">Mean</option>
          <option value="median">Median</option>
          <option value="last_observation">LOCF</option>
        </select>
      </label>
      <label>
        n imputations
        <input
          type="number"
          min={1}
          max={20}
          value={n}
          onChange={(e) => setN(Number(e.target.value))}
          aria-label="n-imputations"
        />
      </label>
      <label>
        Seed
        <input
          type="number"
          value={seed}
          onChange={(e) => setSeed(Number(e.target.value))}
          aria-label="seed"
        />
      </label>
      <fieldset>
        <legend>Target columns</legend>
        {numericColumns.map((c) => (
          <label key={c}>
            <input
              type="checkbox"
              checked={selected.includes(c)}
              onChange={(e) =>
                setSelected(
                  e.target.checked
                    ? [...selected, c]
                    : selected.filter((x) => x !== c),
                )
              }
            />
            {c}
          </label>
        ))}
      </fieldset>
      <button
        onClick={() => runMutation.mutate()}
        disabled={selected.length === 0 || runMutation.isPending}
      >
        Run imputation
      </button>
      {runMutation.error ? (
        <div
          role="alert"
          data-testid="imputation-error"
          style={{
            color: '#b91c1c',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            padding: '6px 10px',
            borderRadius: 4,
            marginTop: 8,
          }}
        >
          {(runMutation.error as Error).message}
        </div>
      ) : null}
      {runMutation.data ? (
        <ImputationResultPanel pooled={runMutation.data.pooled_summary} />
      ) : null}
      {history ? (
        <details>
          <summary>{history.length} previous run(s)</summary>
          <ul>
            {history.map((h) => (
              <li key={h.id}>
                {h.method} × {h.n_imputations} (seed {h.seed})
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </div>
  )
}

function ImputationResultPanel({ pooled }: { pooled: Record<string, unknown> }) {
  // ``pooled_summary`` from the backend is a dict of column → {pooled_mean,
  // total_variance, df}. Render as a table; collapse the raw JSON for power
  // users who want the original blob.
  const entries = Object.entries(pooled ?? {}).filter(
    ([, v]) => v && typeof v === 'object',
  ) as Array<[string, Record<string, unknown>]>
  if (entries.length === 0) {
    return (
      <p data-testid="imputation-result" style={{ marginTop: 8, fontSize: 12 }}>
        No pooled summary returned.
      </p>
    )
  }
  const fmt = (v: unknown): string => {
    if (typeof v !== 'number' || !Number.isFinite(v)) return '—'
    return Math.abs(v) >= 100 ? v.toFixed(1) : v.toFixed(3)
  }
  return (
    <div data-testid="imputation-result" style={{ marginTop: 8 }}>
      <table style={{ borderCollapse: 'collapse', fontSize: 12 }}>
        <thead>
          <tr>
            <th style={{ textAlign: 'left', padding: '2px 6px' }}>Column</th>
            <th style={{ textAlign: 'right', padding: '2px 6px' }}>
              Pooled mean
            </th>
            <th style={{ textAlign: 'right', padding: '2px 6px' }}>
              Total variance
            </th>
            <th style={{ textAlign: 'right', padding: '2px 6px' }}>df</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([col, summary]) => (
            <tr key={col}>
              <td style={{ padding: '2px 6px' }}>{col}</td>
              <td style={{ textAlign: 'right', padding: '2px 6px' }}>
                {fmt(summary.pooled_mean)}
              </td>
              <td style={{ textAlign: 'right', padding: '2px 6px' }}>
                {fmt(summary.total_variance)}
              </td>
              <td style={{ textAlign: 'right', padding: '2px 6px' }}>
                {fmt(summary.df)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <details style={{ marginTop: 6 }}>
        <summary style={{ cursor: 'pointer', fontSize: 11 }}>Raw output</summary>
        <pre style={{ fontSize: 10, marginTop: 4 }}>
          {JSON.stringify(pooled, null, 2)}
        </pre>
      </details>
    </div>
  )
}

export default ImputationCard
