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
      {runMutation.data ? (
        <pre data-testid="imputation-result">
          {JSON.stringify(runMutation.data.pooled_summary, null, 2)}
        </pre>
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

export default ImputationCard
