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

export function SurvivalWizard({
  projectId,
  dataset,
}: {
  projectId: string
  dataset: Dataset
}) {
  const [time, setTime] = useState<string | null>(null)
  const [event, setEvent] = useState<string | null>(null)
  const [strata, setStrata] = useState<string | null>(null)
  const [predictors, setPredictors] = useState<string[]>([])
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<PathwayResponse | null>(null)

  const submit = async () => {
    if (!time || !event) {
      toast.error('Pick time + event columns')
      return
    }
    setRunning(true)
    try {
      const r = await pathwaysApi.runSurvival(projectId, dataset.id, {
        time,
        event,
        strata: strata ?? undefined,
        predictors: predictors.length ? predictors : undefined,
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
        <h2 className="text-base font-semibold">Time to event / survival</h2>
        <p className="text-sm text-muted-foreground">
          Kaplan-Meier curves and optional log-rank + Cox proportional hazards.
        </p>
      </header>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <ColumnPicker
          label="Time column"
          variables={dataset.variables}
          value={time}
          onChange={setTime}
          acceptedTypes={['numeric', 'time']}
          helpText="Numeric (days/months/years to event or censoring)."
        />
        <ColumnPicker
          label="Event column (0/1)"
          variables={dataset.variables}
          value={event}
          onChange={setEvent}
          acceptedTypes={['event_indicator', 'numeric', 'nominal']}
          helpText="1 = event observed, 0 = censored."
        />
      </div>
      <ColumnPicker
        label="Strata (optional)"
        variables={dataset.variables}
        value={strata}
        onChange={setStrata}
        acceptedTypes={['nominal', 'ordinal', 'unknown']}
        helpText="Group column for KM curves + log-rank."
      />
      <MultiColumnPicker
        label="Cox predictors (optional)"
        variables={dataset.variables}
        value={predictors}
        onChange={setPredictors}
        helpText="Pick one or more covariates for Cox proportional hazards."
      />
      <Button onClick={submit} disabled={running || !time || !event}>
        {running ? 'Running...' : 'Run pathway'}
      </Button>
      {result ? (
        <PathwayResultCard
          projectId={projectId}
          datasetId={dataset.id}
          response={result}
        >
          <SurvivalSummary result={result.result} />
        </PathwayResultCard>
      ) : null}
    </div>
  )
}

function SurvivalSummary({ result }: { result: Record<string, unknown> }) {
  const overall = (result.overall as Record<string, unknown>) ?? {}
  const lr = result.logrank as { p_value?: number } | undefined
  const cox = result.cox as { terms?: Array<{ term: string; estimate: number; p_value: number; ci_low: number; ci_high: number }>; ph_assumption?: { global_p?: number; violated?: boolean } } | undefined
  return (
    <dl
      className="grid grid-cols-2 gap-3 rounded border border-border bg-muted/40 p-3 text-xs"
      data-testid="survival-summary"
    >
      <div>
        <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">n / events</dt>
        <dd className="font-mono text-sm">
          {String(result.n ?? '?')} / {String(result.n_events ?? '?')}
        </dd>
      </div>
      <div>
        <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">Median survival</dt>
        <dd className="font-mono text-sm">
          {overall.median_survival == null
            ? 'not reached'
            : Number(overall.median_survival).toFixed(1)}
        </dd>
      </div>
      {lr?.p_value != null ? (
        <div className="col-span-2">
          <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">Log-rank</dt>
          <dd className="font-mono text-sm">
            {lr.p_value < 0.001 ? 'p<0.001' : `p=${lr.p_value.toFixed(3)}`}
          </dd>
        </div>
      ) : null}
      {cox?.terms && cox.terms.length > 0 ? (
        <div className="col-span-2">
          <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">Cox HRs</dt>
          <ul className="font-mono text-xs space-y-0.5">
            {cox.terms.map((t) => (
              <li key={t.term}>
                {t.term}: HR={t.estimate.toFixed(2)} ({t.ci_low.toFixed(2)} to{' '}
                {t.ci_high.toFixed(2)}; p={t.p_value.toFixed(3)})
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </dl>
  )
}
