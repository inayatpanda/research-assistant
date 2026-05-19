/**
 * Phase 17 (MP17) — Inter-rater reliability panel.
 *
 * Picker for Fleiss / Krippendorff / weighted-kappa with the requisite
 * input matrices typed in via the UI (CSV-style textareas).
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import { irrApi } from '../../lib/api'

interface Props {
  projectId: string
  datasetId: string
}

function parseMatrix(text: string): number[][] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) =>
      line.split(/[\s,]+/).map((cell) => (cell === '' || cell === 'NA' ? Number.NaN : Number(cell))),
    )
}

export function IRRPanel({ projectId, datasetId }: Props) {
  const [method, setMethod] = useState<'fleiss' | 'krippendorff' | 'weighted_kappa'>('fleiss')
  const [text, setText] = useState('')
  const [level, setLevel] = useState<'nominal' | 'ordinal' | 'interval'>('nominal')
  const [weights, setWeights] = useState<'linear' | 'quadratic'>('linear')

  const runMutation = useMutation({
    mutationFn: async () => {
      if (method === 'fleiss') {
        const matrix = parseMatrix(text)
        return irrApi.fleiss(projectId, datasetId, matrix)
      }
      if (method === 'krippendorff') {
        const matrix = parseMatrix(text).map((row) =>
          row.map((v) => (Number.isNaN(v) ? null : v)),
        )
        return irrApi.krippendorff(projectId, datasetId, matrix, level)
      }
      const rows = parseMatrix(text)
      const rater1 = rows.map((r) => r[0]).filter((v) => !Number.isNaN(v))
      const rater2 = rows.map((r) => r[1]).filter((v) => !Number.isNaN(v))
      return irrApi.weightedKappa(projectId, datasetId, rater1, rater2, weights, 0)
    },
  })

  return (
    <div data-testid="irr-panel">
      <h4>Inter-rater reliability</h4>
      <label>
        Method
        <select value={method} onChange={(e) => setMethod(e.target.value as never)}>
          <option value="fleiss">Fleiss κ</option>
          <option value="krippendorff">Krippendorff α</option>
          <option value="weighted_kappa">Weighted κ (two raters)</option>
        </select>
      </label>
      {method === 'krippendorff' ? (
        <label>
          Level
          <select value={level} onChange={(e) => setLevel(e.target.value as never)}>
            <option value="nominal">nominal</option>
            <option value="ordinal">ordinal</option>
            <option value="interval">interval</option>
          </select>
        </label>
      ) : null}
      {method === 'weighted_kappa' ? (
        <label>
          Weights
          <select value={weights} onChange={(e) => setWeights(e.target.value as never)}>
            <option value="linear">linear</option>
            <option value="quadratic">quadratic</option>
          </select>
        </label>
      ) : null}
      <textarea
        aria-label="ratings-matrix"
        rows={6}
        placeholder="Paste matrix (rows = subjects; cells = counts or raw ratings)"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button onClick={() => runMutation.mutate()} disabled={!text || runMutation.isPending}>
        Compute
      </button>
      {runMutation.error ? (
        <div
          role="alert"
          data-testid="irr-error"
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
        <IRRResultPanel method={method} data={runMutation.data} />
      ) : null}
    </div>
  )
}

function IRRResultPanel({
  method,
  data,
}: {
  method: 'fleiss' | 'krippendorff' | 'weighted_kappa'
  data: Record<string, unknown>
}) {
  // Render the key stats with formatted numbers + a collapsed raw blob.
  const stat = (k: string): string => {
    const v = data[k]
    if (typeof v === 'number' && Number.isFinite(v)) {
      return Math.abs(v) < 1 ? v.toFixed(3) : v.toFixed(2)
    }
    return String(v ?? '—')
  }
  return (
    <div data-testid="irr-result" style={{ marginTop: 8 }}>
      {method === 'fleiss' ? (
        <dl>
          <dt>Fleiss κ</dt>
          <dd>{stat('kappa')}</dd>
          <dt>Subjects</dt>
          <dd>{stat('n_subjects')}</dd>
          <dt>Raters</dt>
          <dd>{stat('n_raters')}</dd>
        </dl>
      ) : null}
      {method === 'krippendorff' ? (
        <dl>
          <dt>Krippendorff α</dt>
          <dd>{stat('alpha')}</dd>
          <dt>Level</dt>
          <dd>{stat('level')}</dd>
          <dt>Units (subjects)</dt>
          <dd>{stat('n_units')}</dd>
        </dl>
      ) : null}
      {method === 'weighted_kappa' ? (
        <dl>
          <dt>Weighted κ</dt>
          <dd>{stat('kappa')}</dd>
          <dt>Weights</dt>
          <dd>{stat('weights')}</dd>
          <dt>95% CI</dt>
          <dd>
            {typeof data.ci_low === 'number' && typeof data.ci_high === 'number'
              ? `[${(data.ci_low as number).toFixed(3)}, ${(data.ci_high as number).toFixed(3)}]`
              : '—'}
          </dd>
        </dl>
      ) : null}
      <details style={{ marginTop: 6 }}>
        <summary style={{ cursor: 'pointer', fontSize: 12 }}>
          Raw output
        </summary>
        <pre style={{ fontSize: 11, marginTop: 4 }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      </details>
    </div>
  )
}

export default IRRPanel
