/**
 * Phase 17 (MP17) — Complier-Average Causal Effect (2SLS) panel.
 *
 * The user picks the assignment column, the treatment-received column and
 * the outcome; the backend runs IV2SLS and returns the CACE point estimate
 * + SE + p-value + compliance rate.
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import { caceApi } from '../../lib/api'

interface Props {
  projectId: string
  analysisId: string
  variables: string[]
}

export function CACEPanel({ projectId, analysisId, variables }: Props) {
  const [outcome, setOutcome] = useState('')
  const [assigned, setAssigned] = useState('')
  const [received, setReceived] = useState('')

  const runMutation = useMutation({
    mutationFn: () => caceApi.run(projectId, analysisId, { outcome, assigned, received }),
  })

  return (
    <div data-testid="cace-panel">
      <h4>Complier-Average Causal Effect (CACE / 2SLS)</h4>
      {(['outcome', 'assigned', 'received'] as const).map((field) => (
        <label key={field}>
          {field}
          <select
            aria-label={field}
            value={field === 'outcome' ? outcome : field === 'assigned' ? assigned : received}
            onChange={(e) => {
              const v = e.target.value
              if (field === 'outcome') setOutcome(v)
              else if (field === 'assigned') setAssigned(v)
              else setReceived(v)
            }}
          >
            <option value="">—</option>
            {variables.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>
      ))}
      <button
        onClick={() => runMutation.mutate()}
        disabled={!outcome || !assigned || !received || runMutation.isPending}
      >
        Compute CACE
      </button>
      {runMutation.data ? (
        <dl>
          <dt>CACE estimate</dt>
          <dd>{runMutation.data.cace_estimate.toFixed(3)}</dd>
          <dt>SE</dt>
          <dd>{runMutation.data.se.toFixed(3)}</dd>
          <dt>p</dt>
          <dd>{runMutation.data.p.toFixed(4)}</dd>
          <dt>Compliance rate</dt>
          <dd>{(runMutation.data.compliance_rate * 100).toFixed(1)}%</dd>
        </dl>
      ) : null}
    </div>
  )
}

export default CACEPanel
