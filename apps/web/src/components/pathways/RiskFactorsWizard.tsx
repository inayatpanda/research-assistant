import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  pathwaysApi,
  type Dataset,
  type PathwayResponse,
} from '@/lib/api'

import { ColumnPicker, MultiColumnPicker } from './ColumnPicker'
import { PathwayResultCard } from './PathwayResultCard'

export type RiskFactorsWizardProps = {
  projectId: string
  dataset: Dataset
}

export function RiskFactorsWizard({
  projectId,
  dataset,
}: RiskFactorsWizardProps) {
  const [outcome, setOutcome] = useState<string | null>(null)
  const [predictors, setPredictors] = useState<string[]>([])
  const [confounders, setConfounders] = useState<string[]>([])
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<PathwayResponse | null>(null)

  const submit = async () => {
    if (!outcome || predictors.length === 0) {
      toast.error('Pick an outcome + at least one predictor')
      return
    }
    setRunning(true)
    try {
      const r = await pathwaysApi.runRiskFactors(projectId, dataset.id, {
        outcome,
        predictors,
        confounders: confounders.length ? confounders : undefined,
      })
      setResult(r)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Pathway failed')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="space-y-4">
      <header>
        <h2 className="text-base font-semibold">Risk factor identification</h2>
        <p className="text-sm text-muted-foreground">
          Univariable and multivariable regression side-by-side. Binary outcomes
          give logistic ORs, continuous outcomes give linear betas, both with
          95% CIs and omnibus model fit.
        </p>
      </header>
      <ColumnPicker
        label="Outcome column"
        variables={dataset.variables}
        value={outcome}
        onChange={setOutcome}
        helpText="Binary (0/1) for logistic regression, numeric for linear regression."
      />
      <MultiColumnPicker
        label="Predictors"
        variables={dataset.variables}
        value={predictors}
        onChange={setPredictors}
        helpText="Pick one or more candidate predictors."
      />
      <MultiColumnPicker
        label="Confounders (optional)"
        variables={dataset.variables}
        value={confounders}
        onChange={setConfounders}
        helpText="Forced into the multivariable model alongside predictors."
      />
      <Button onClick={submit} disabled={running || !outcome || !predictors.length}>
        {running ? 'Running...' : 'Run pathway'}
      </Button>
      {result ? (
        <PathwayResultCard
          projectId={projectId}
          datasetId={dataset.id}
          response={result}
        >
          <RiskFactorsTable result={result.result} />
        </PathwayResultCard>
      ) : null}
    </div>
  )
}

type RegressionRow = {
  term: string
  estimate: number | null
  estimate_label: string
  ci_low: number | null
  ci_high: number | null
  p_value: number | null
  error?: string
}

function RiskFactorsTable({ result }: { result: Record<string, unknown> }) {
  const univariable = (result.univariable as RegressionRow[]) ?? []
  const multivariable = (result.multivariable as RegressionRow[]) ?? []
  const byTerm = new Map<string, { uni?: RegressionRow; mv?: RegressionRow }>()
  for (const row of univariable) {
    byTerm.set(row.term, { ...(byTerm.get(row.term) ?? {}), uni: row })
  }
  for (const row of multivariable) {
    byTerm.set(row.term, { ...(byTerm.get(row.term) ?? {}), mv: row })
  }
  return (
    <div className="overflow-auto" data-testid="risk-factors-table">
      <table className="min-w-full text-xs">
        <thead>
          <tr className="border-b border-border text-left text-muted-foreground">
            <th className="py-1.5 pr-2">Variable</th>
            <th className="py-1.5 pr-2">Unadjusted</th>
            <th className="py-1.5 pr-2">Adjusted</th>
          </tr>
        </thead>
        <tbody>
          {Array.from(byTerm.entries()).map(([term, rows]) => (
            <tr key={term} className="border-b border-border/50">
              <td className="py-1 pr-2 font-medium">{term}</td>
              <td className="py-1 pr-2 font-mono">{cell(rows.uni)}</td>
              <td className="py-1 pr-2 font-mono">{cell(rows.mv)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function cell(r: RegressionRow | undefined): string {
  if (!r) return '—'
  if (r.error) return 'err'
  if (r.estimate == null) return '—'
  const ci =
    r.ci_low != null && r.ci_high != null
      ? `${r.ci_low.toFixed(2)} to ${r.ci_high.toFixed(2)}`
      : '—'
  const p =
    r.p_value == null
      ? ''
      : r.p_value < 0.001
        ? '; p<0.001'
        : `; p=${r.p_value.toFixed(3)}`
  return `${r.estimate_label}=${r.estimate.toFixed(2)} (${ci}${p})`
}
