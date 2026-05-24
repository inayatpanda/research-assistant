import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  pathwaysApi,
  type Dataset,
  type PathwayResponse,
} from '@/lib/api'

import { ColumnPicker } from './ColumnPicker'
import { PathwayResultCard } from './PathwayResultCard'

export function AgreementWizard({
  projectId,
  dataset,
}: {
  projectId: string
  dataset: Dataset
}) {
  const [raterA, setRaterA] = useState<string | null>(null)
  const [raterB, setRaterB] = useState<string | null>(null)
  const [ordinal, setOrdinal] = useState(false)
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<PathwayResponse | null>(null)

  const submit = async () => {
    if (!raterA || !raterB) {
      toast.error('Pick both rater columns')
      return
    }
    if (raterA === raterB) {
      toast.error('Rater columns must differ')
      return
    }
    setRunning(true)
    try {
      const r = await pathwaysApi.runAgreement(projectId, dataset.id, {
        rater_a: raterA,
        rater_b: raterB,
        ordinal: ordinal || undefined,
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
        <h2 className="text-base font-semibold">Agreement / reliability</h2>
        <p className="text-sm text-muted-foreground">
          ICC + Bland-Altman for continuous raters, Cohen&apos;s kappa
          (unweighted + weighted) for categorical raters.
        </p>
      </header>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <ColumnPicker
          label="Rater 1"
          variables={dataset.variables}
          value={raterA}
          onChange={setRaterA}
        />
        <ColumnPicker
          label="Rater 2"
          variables={dataset.variables}
          value={raterB}
          onChange={setRaterB}
        />
      </div>
      <label className="flex items-center gap-2 text-xs text-muted-foreground">
        <input
          type="checkbox"
          checked={ordinal}
          onChange={(e) => setOrdinal(e.target.checked)}
        />
        <Label className="text-xs">Categorical raters are ordinal (use weighted kappa)</Label>
      </label>
      <Button onClick={submit} disabled={running || !raterA || !raterB}>
        {running ? 'Running...' : 'Run pathway'}
      </Button>
      {result ? (
        <PathwayResultCard
          projectId={projectId}
          datasetId={dataset.id}
          response={result}
        >
          <AgreementSummary result={result.result} />
        </PathwayResultCard>
      ) : null}
    </div>
  )
}

function AgreementSummary({ result }: { result: Record<string, unknown> }) {
  const dataType = String(result.data_type ?? '')
  if (dataType === 'continuous') {
    const icc = (result.icc as Record<string, number>) ?? {}
    const ba = (result.bland_altman as Record<string, number>) ?? {}
    return (
      <dl
        className="grid grid-cols-3 gap-3 rounded border border-border bg-muted/40 p-3 text-xs"
        data-testid="agreement-summary"
      >
        <div>
          <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">ICC</dt>
          <dd className="font-mono text-sm">{Number(icc.icc).toFixed(3)}</dd>
        </div>
        <div>
          <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">Bias</dt>
          <dd className="font-mono text-sm">{Number(ba.bias).toFixed(3)}</dd>
        </div>
        <div>
          <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">95% LOA</dt>
          <dd className="font-mono text-sm">
            {Number(ba.loa_low).toFixed(2)} to {Number(ba.loa_high).toFixed(2)}
          </dd>
        </div>
      </dl>
    )
  }
  const k = (result.kappa as Record<string, number>) ?? {}
  const w = result.weighted_kappa as Record<string, number> | undefined
  return (
    <dl
      className="grid grid-cols-2 gap-3 rounded border border-border bg-muted/40 p-3 text-xs"
      data-testid="agreement-summary"
    >
      <div>
        <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">Cohen&apos;s kappa</dt>
        <dd className="font-mono text-sm">{Number(k.kappa).toFixed(3)}</dd>
      </div>
      {w ? (
        <div>
          <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">Weighted kappa</dt>
          <dd className="font-mono text-sm">{Number(w.kappa).toFixed(3)}</dd>
        </div>
      ) : null}
    </dl>
  )
}
