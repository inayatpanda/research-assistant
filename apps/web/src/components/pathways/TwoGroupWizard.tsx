import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  pathwaysApi,
  type Dataset,
  type PathwayResponse,
} from '@/lib/api'

import { ColumnPicker } from './ColumnPicker'
import { PathwayResultCard } from './PathwayResultCard'

export type TwoGroupWizardProps = {
  projectId: string
  dataset: Dataset
}

export function TwoGroupWizard({ projectId, dataset }: TwoGroupWizardProps) {
  const [outcome, setOutcome] = useState<string | null>(null)
  const [group, setGroup] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<PathwayResponse | null>(null)

  const submit = async () => {
    if (!outcome || !group) {
      toast.error('Pick outcome + group')
      return
    }
    setRunning(true)
    try {
      const r = await pathwaysApi.runTwoGroup(projectId, dataset.id, {
        outcome,
        group,
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
        <h2 className="text-base font-semibold">Two-group comparison</h2>
        <p className="text-sm text-muted-foreground">
          Compare an outcome between groups A and B. The app picks the right
          test (t-test, Welch, Mann-Whitney, chi-square, or Fisher) based on the
          column types and normality of your data.
        </p>
      </header>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <ColumnPicker
          label="Outcome column"
          variables={dataset.variables}
          value={outcome}
          onChange={setOutcome}
          helpText="Numeric or categorical column."
        />
        <ColumnPicker
          label="Group column (2 levels)"
          variables={dataset.variables}
          value={group}
          onChange={setGroup}
          acceptedTypes={['nominal', 'ordinal', 'unknown']}
          helpText="Categorical column with exactly two distinct values."
        />
      </div>
      <Button onClick={submit} disabled={running || !outcome || !group}>
        {running ? 'Running...' : 'Run pathway'}
      </Button>
      {result ? (
        <PathwayResultCard
          projectId={projectId}
          datasetId={dataset.id}
          response={result}
        >
          <TwoGroupSummary result={result.result} />
        </PathwayResultCard>
      ) : null}
    </div>
  )
}

function TwoGroupSummary({ result }: { result: Record<string, unknown> }) {
  const testUsed = String(result.test_used ?? '')
  const pStr = formatP(result.p_value as number | null | undefined)
  return (
    <dl
      className="grid grid-cols-3 gap-3 rounded border border-border bg-muted/40 p-3 text-xs"
      data-testid="two-group-summary"
    >
      <Stat label="Test" value={prettyTest(testUsed)} />
      <Stat label="p-value" value={pStr} />
      <Stat
        label="Effect"
        value={
          (result.effect_size as number | null) != null
            ? `${result.effect_label}: ${formatNum(result.effect_size as number)}`
            : '—'
        }
      />
    </dl>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">
        {label}
      </dt>
      <dd className="font-mono text-sm">{value}</dd>
    </div>
  )
}

function formatP(p: number | null | undefined): string {
  if (p == null || Number.isNaN(p)) return 'NA'
  if (p < 0.001) return 'p<0.001'
  return `p=${p.toFixed(3)}`
}

function formatNum(v: number | null | undefined, d = 2): string {
  if (v == null || Number.isNaN(v)) return 'NA'
  return v.toFixed(d)
}

function prettyTest(key: string): string {
  switch (key) {
    case 'student_t':
      return "Student's t-test"
    case 'welch_t':
      return "Welch's t-test"
    case 'mann_whitney':
      return 'Mann-Whitney U'
    case 'chi_squared':
      return 'Chi-squared'
    case 'fisher_exact':
      return "Fisher's exact"
    default:
      return key
  }
}
