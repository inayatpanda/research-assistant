/**
 * Phase 17 (MP17) — Auto-rendered post-hoc pairwise comparison card.
 *
 * Mount underneath an ANOVA or Kruskal-Wallis result; the parent passes
 * the omnibus p-value so we can gate the “run post-hoc” button.
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import { postHocApi, type PostHocPair } from '../../lib/api'

interface Props {
  projectId: string
  analysisId: string
  outcome: string
  groups: string
  omnibusPValue: number
  alpha?: number
  defaultMethod?: 'tukey' | 'bonferroni' | 'dunns' | 'games_howell'
}

export function PostHocComparisonsCard({
  projectId,
  analysisId,
  outcome,
  groups,
  omnibusPValue,
  alpha = 0.05,
  defaultMethod = 'tukey',
}: Props) {
  const [method, setMethod] = useState(defaultMethod)
  const recommended = omnibusPValue < alpha

  const runMutation = useMutation({
    mutationFn: () =>
      postHocApi.run(projectId, analysisId, { method, outcome, groups }),
  })

  return (
    <div className="posthoc-card" data-testid="posthoc-card">
      <h4>Post-hoc pairwise comparisons</h4>
      <p>
        Omnibus p-value: <strong>{omnibusPValue.toFixed(4)}</strong>
        {recommended ? ' — pairwise follow-up suggested.' : ' — no follow-up needed.'}
      </p>
      <label>
        Method
        <select value={method} onChange={(e) => setMethod(e.target.value as never)}>
          <option value="tukey">Tukey HSD</option>
          <option value="bonferroni">Bonferroni-corrected t-tests</option>
          <option value="dunns">Dunn's (non-parametric)</option>
          <option value="games_howell">Games-Howell (unequal variance)</option>
        </select>
      </label>
      <button onClick={() => runMutation.mutate()} disabled={runMutation.isPending}>
        Run post-hoc
      </button>
      {runMutation.data ? (
        <table>
          <thead>
            <tr>
              <th>Pair</th>
              <th>Mean diff</th>
              <th>p (adj.)</th>
            </tr>
          </thead>
          <tbody>
            {runMutation.data.pairs.map((p: PostHocPair, i: number) => (
              <tr key={i}>
                <td>{p.pair.join(' vs ')}</td>
                <td>{p.mean_diff.toFixed(3)}</td>
                <td>{p.p_adj.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  )
}

export default PostHocComparisonsCard
