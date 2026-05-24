import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  pathwaysApi,
  type Dataset,
  type PathwayResponse,
} from '@/lib/api'

import { ColumnPicker } from './ColumnPicker'
import { PathwayResultCard } from './PathwayResultCard'

export function DiagnosticWizard({
  projectId,
  dataset,
}: {
  projectId: string
  dataset: Dataset
}) {
  const [test, setTest] = useState<string | null>(null)
  const [reference, setReference] = useState<string | null>(null)
  const [preTest, setPreTest] = useState<string>('')
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<PathwayResponse | null>(null)

  const submit = async () => {
    if (!test || !reference) {
      toast.error('Pick test + reference columns')
      return
    }
    let pre: number | undefined
    if (preTest.trim().length) {
      const n = Number(preTest)
      if (!(n > 0 && n < 1)) {
        toast.error('Pre-test probability must be between 0 and 1')
        return
      }
      pre = n
    }
    setRunning(true)
    try {
      const r = await pathwaysApi.runDiagnostic(projectId, dataset.id, {
        test,
        reference,
        pre_test_probability: pre,
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
        <h2 className="text-base font-semibold">Diagnostic accuracy</h2>
        <p className="text-sm text-muted-foreground">
          ROC + AUC for continuous tests, 2x2 sensitivity / specificity / PPV /
          NPV for binary tests, with optional Bayes post-test probability.
        </p>
      </header>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <ColumnPicker
          label="Test result column"
          variables={dataset.variables}
          value={test}
          onChange={setTest}
          helpText="Numeric (continuous test) or binary (already-thresholded)."
        />
        <ColumnPicker
          label="Reference standard (binary)"
          variables={dataset.variables}
          value={reference}
          onChange={setReference}
          acceptedTypes={['event_indicator', 'nominal', 'numeric']}
          helpText="Gold standard: 1 = condition present, 0 = absent."
        />
      </div>
      <div>
        <Label htmlFor="pretest-prob" className="text-xs font-medium text-muted-foreground">
          Pre-test probability (optional, 0-1)
        </Label>
        <Input
          id="pretest-prob"
          value={preTest}
          onChange={(e) => setPreTest(e.target.value)}
          placeholder="e.g. 0.2"
          className="max-w-[160px]"
        />
      </div>
      <Button onClick={submit} disabled={running || !test || !reference}>
        {running ? 'Running...' : 'Run pathway'}
      </Button>
      {result ? (
        <PathwayResultCard
          projectId={projectId}
          datasetId={dataset.id}
          response={result}
        >
          <DiagnosticSummary result={result.result} />
        </PathwayResultCard>
      ) : null}
    </div>
  )
}

function DiagnosticSummary({ result }: { result: Record<string, unknown> }) {
  const isContinuous = result.test_type === 'continuous'
  const metrics = (
    isContinuous
      ? (result.at_optimal as Record<string, unknown>)
      : (result.metrics as Record<string, unknown>)
  ) ?? {}
  return (
    <dl
      className="grid grid-cols-2 gap-3 rounded border border-border bg-muted/40 p-3 text-xs md:grid-cols-4"
      data-testid="diagnostic-summary"
    >
      {isContinuous ? (
        <div>
          <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">AUC</dt>
          <dd className="font-mono text-sm">
            {Number(result.auc).toFixed(3)}
          </dd>
        </div>
      ) : null}
      <div>
        <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">Sens</dt>
        <dd className="font-mono text-sm">
          {Number(metrics.sensitivity).toFixed(3)}
        </dd>
      </div>
      <div>
        <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">Spec</dt>
        <dd className="font-mono text-sm">
          {Number(metrics.specificity).toFixed(3)}
        </dd>
      </div>
      <div>
        <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">PPV / NPV</dt>
        <dd className="font-mono text-sm">
          {Number(metrics.ppv).toFixed(2)} / {Number(metrics.npv).toFixed(2)}
        </dd>
      </div>
    </dl>
  )
}
