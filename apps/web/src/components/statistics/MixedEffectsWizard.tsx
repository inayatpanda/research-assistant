/**
 * Phase 17 (MP17) — Mixed-effects setup wizard.
 *
 * Composes the `variables` dict for chosen_test=mixed_effects_lm, including
 * the new MP17 fields: ``inner_cluster``, ``reml``, ``interaction_pair``.
 * The component is intentionally a thin form-builder — the parent dispatches
 * the actual analysis create through the existing analyses workflow.
 */
import { useEffect, useState } from 'react'

export interface MixedEffectsConfig {
  outcome: string
  predictors: string[]
  cluster: string
  inner_cluster?: string
  reml: boolean
  interaction_pair?: [string, string]
}

interface Props {
  variables: string[]
  onChange: (config: MixedEffectsConfig) => void
}

export function MixedEffectsWizard({ variables, onChange }: Props) {
  const [outcome, setOutcome] = useState('')
  const [predictors, setPredictors] = useState<string[]>([])
  const [cluster, setCluster] = useState('')
  const [innerCluster, setInnerCluster] = useState('')
  const [reml, setReml] = useState(true)
  const [interactionEnabled, setInteractionEnabled] = useState(false)
  const [interactionA, setInteractionA] = useState('')
  const [interactionB, setInteractionB] = useState('')

  // Pre-stats-refine, this component called `emit()` inline after each
  // setState — which captured the *stale* state and emitted the pre-edit
  // config every time. Now we derive `onChange` from the post-state via
  // an effect, so the parent always sees the latest config exactly once
  // per state change.
  useEffect(() => {
    onChange({
      outcome,
      predictors,
      cluster,
      inner_cluster: innerCluster || undefined,
      reml,
      interaction_pair:
        interactionEnabled && interactionA && interactionB
          ? [interactionA, interactionB]
          : undefined,
    })
    // We intentionally don't include onChange in deps — parents may pass
    // a fresh fn every render and we'd loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    outcome,
    predictors,
    cluster,
    innerCluster,
    reml,
    interactionEnabled,
    interactionA,
    interactionB,
  ])

  return (
    <div data-testid="mixed-effects-wizard">
      <h4>Mixed-effects setup</h4>
      <label>
        Outcome
        <select
          value={outcome}
          onChange={(e) => setOutcome(e.target.value)}
        >
          <option value="">—</option>
          {variables.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      </label>
      <label>
        Cluster
        <select
          value={cluster}
          onChange={(e) => setCluster(e.target.value)}
        >
          <option value="">—</option>
          {variables.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      </label>
      <label>
        Nested inner cluster (optional)
        <select
          value={innerCluster}
          onChange={(e) => setInnerCluster(e.target.value)}
        >
          <option value="">— (none)</option>
          {variables.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
      </label>
      <fieldset>
        <legend>Estimation</legend>
        <label>
          <input
            type="radio"
            name="estimation"
            checked={reml}
            onChange={() => setReml(true)}
          />
          REML
        </label>
        <label>
          <input
            type="radio"
            name="estimation"
            checked={!reml}
            onChange={() => setReml(false)}
          />
          ML
        </label>
      </fieldset>
      <label>
        <input
          type="checkbox"
          checked={interactionEnabled}
          onChange={(e) => setInteractionEnabled(e.target.checked)}
        />
        Treatment × time interaction
      </label>
      {interactionEnabled ? (
        <>
          <select
            value={interactionA}
            onChange={(e) => setInteractionA(e.target.value)}
            aria-label="interaction-a"
          >
            <option value="">—</option>
            {variables.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
          <select
            value={interactionB}
            onChange={(e) => setInteractionB(e.target.value)}
            aria-label="interaction-b"
          >
            <option value="">—</option>
            {variables.map((v) => <option key={v} value={v}>{v}</option>)}
          </select>
        </>
      ) : null}
      <label>
        Predictors (comma-separated)
        <input
          aria-label="predictors"
          value={predictors.join(', ')}
          onChange={(e) =>
            setPredictors(
              e.target.value.split(',').map((s) => s.trim()).filter(Boolean),
            )
          }
        />
      </label>
    </div>
  )
}

export default MixedEffectsWizard
