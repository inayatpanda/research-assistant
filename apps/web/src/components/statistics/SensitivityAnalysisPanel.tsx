/**
 * Phase 17 (MP17) — Missing-data sensitivity-analysis panel.
 *
 * Worst-case / best-case / tipping-point analyses for a 2-arm comparison.
 * Tipping-point exposes an explicit candidate-low / candidate-high bracket
 * so users can constrain the bisection range.
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import { sensitivityApi } from '../../lib/api'

interface Props {
  projectId: string
  analysisId: string
  variables: string[]
}

export function SensitivityAnalysisPanel({ projectId, analysisId, variables }: Props) {
  const [type, setType] = useState<'worst_case' | 'best_case' | 'tipping_point'>('worst_case')
  const [outcome, setOutcome] = useState('')
  const [group, setGroup] = useState('')
  const [candidateLow, setCandidateLow] = useState<number | ''>('')
  const [candidateHigh, setCandidateHigh] = useState<number | ''>('')

  const runMutation = useMutation({
    mutationFn: () =>
      sensitivityApi.run(projectId, analysisId, {
        type,
        outcome,
        group,
        candidate_low: candidateLow === '' ? null : candidateLow,
        candidate_high: candidateHigh === '' ? null : candidateHigh,
      }),
  })

  return (
    <div data-testid="sensitivity-panel">
      <h4>Missing-data sensitivity</h4>
      <label>
        Type
        <select value={type} onChange={(e) => setType(e.target.value as never)}>
          <option value="worst_case">Worst-case</option>
          <option value="best_case">Best-case</option>
          <option value="tipping_point">Tipping point</option>
        </select>
      </label>
      <label>
        Outcome
        <select aria-label="outcome" value={outcome} onChange={(e) => setOutcome(e.target.value)}>
          <option value="">—</option>
          {variables.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      </label>
      <label>
        Group (2 levels)
        <select aria-label="group" value={group} onChange={(e) => setGroup(e.target.value)}>
          <option value="">—</option>
          {variables.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      </label>
      {type === 'tipping_point' ? (
        <>
          <label>
            Candidate low
            <input
              type="number"
              aria-label="candidate-low"
              value={candidateLow}
              onChange={(e) => setCandidateLow(e.target.value === '' ? '' : Number(e.target.value))}
            />
          </label>
          <label>
            Candidate high
            <input
              type="number"
              aria-label="candidate-high"
              value={candidateHigh}
              onChange={(e) => setCandidateHigh(e.target.value === '' ? '' : Number(e.target.value))}
            />
          </label>
        </>
      ) : null}
      <button
        onClick={() => runMutation.mutate()}
        disabled={!outcome || !group || runMutation.isPending}
      >
        Run
      </button>
      {runMutation.data ? (
        <div data-testid="sensitivity-result">
          <p>{runMutation.data.note}</p>
          {runMutation.data.threshold !== null ? (
            <p>Threshold: <strong>{runMutation.data.threshold.toFixed(3)}</strong></p>
          ) : null}
          {runMutation.data.effect_estimate !== null ? (
            <p>Effect estimate: {runMutation.data.effect_estimate.toFixed(3)}</p>
          ) : null}
          {runMutation.data.p_value !== null ? (
            <p>p-value: {runMutation.data.p_value.toFixed(4)}</p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

export default SensitivityAnalysisPanel
