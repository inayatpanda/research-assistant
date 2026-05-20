/**
 * DEMO-FIX-A — Standalone diagnostics panel.
 *
 * The user picks a test (Shapiro-Wilk, Anderson-Darling, KS,
 * D'Agostino-Pearson, Levene, Bartlett, Q-Q plot, or histogram + normal
 * overlay), a numeric column, and (for Levene/Bartlett) a nominal group
 * column.  Clicking Run calls the appropriate `/diagnostics/...`
 * endpoint and renders the result — a stats card with the test statistic,
 * p-value, the human-readable interpretation, plus a green/amber pass/fail
 * pill, or a PNG for the visual diagnostics.
 *
 * Critically this is *additive* — Shapiro-Wilk and Levene continue to run
 * automatically alongside parametric analyses (see `_compute_assumptions`
 * in routes/analyses.py).  This panel just exposes them on demand.
 */
import { AlertTriangle, CheckCircle2, FlaskConical, Loader2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'
import {
  type Dataset,
  type DiagnosticResult,
  type DiagnosticTestKey,
  diagnosticsApi,
  DIAGNOSTIC_NEEDS_GROUP,
  DIAGNOSTIC_TEST_LABELS,
} from '@/lib/api'

type VisualKey = 'qq_plot' | 'histogram_normal'

type PickerKey = DiagnosticTestKey | VisualKey

const VISUAL_LABELS: Record<VisualKey, string> = {
  qq_plot: 'Q-Q plot (vs normal)',
  histogram_normal: 'Histogram + normal overlay',
}

const ORDER: PickerKey[] = [
  'shapiro_wilk',
  'anderson_darling',
  'kolmogorov_smirnov',
  'dagostino_pearson',
  'levene',
  'bartlett',
  'qq_plot',
  'histogram_normal',
]

function isVisual(k: PickerKey): k is VisualKey {
  return k === 'qq_plot' || k === 'histogram_normal'
}

function isStat(k: PickerKey): k is DiagnosticTestKey {
  return !isVisual(k)
}

function needsGroup(k: PickerKey): boolean {
  return isStat(k) && DIAGNOSTIC_NEEDS_GROUP[k]
}

function formatP(p: number | null | undefined): string {
  if (p == null || !Number.isFinite(p)) return 'n/a'
  if (p < 0.001) return '<0.001'
  return p.toFixed(3)
}

export function DiagnosticsPanel({
  projectId,
  dataset,
}: {
  projectId: string
  dataset: Dataset
}) {
  const [testKey, setTestKey] = useState<PickerKey>('shapiro_wilk')
  const [columnName, setColumnName] = useState<string>('')
  const [groupColumn, setGroupColumn] = useState<string>('')
  const [running, setRunning] = useState(false)
  const [statResult, setStatResult] = useState<DiagnosticResult | null>(null)
  const [pngUrl, setPngUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const numericColumns = useMemo(
    () =>
      dataset.variables.filter(
        (v) => (v.user_type ?? v.inferred_type) === 'numeric',
      ),
    [dataset.variables],
  )
  const nominalColumns = useMemo(
    () =>
      dataset.variables.filter((v) => {
        const t = v.user_type ?? v.inferred_type
        return t === 'nominal' || t === 'ordinal'
      }),
    [dataset.variables],
  )

  // Keep the column selection valid as the variables list changes.
  useEffect(() => {
    if (!columnName && numericColumns.length > 0) {
      setColumnName(numericColumns[0].name)
    }
  }, [columnName, numericColumns])

  function labelFor(name: string): string {
    const v = dataset.variables.find((x) => x.name === name)
    return v?.display_label?.trim() || name
  }

  async function onRun() {
    setError(null)
    setStatResult(null)
    if (pngUrl) {
      URL.revokeObjectURL(pngUrl)
      setPngUrl(null)
    }
    if (!columnName) {
      setError('Pick a numeric column first.')
      return
    }
    if (needsGroup(testKey) && !groupColumn) {
      setError('This test needs a group column.')
      return
    }
    setRunning(true)
    try {
      if (testKey === 'qq_plot') {
        const url = await diagnosticsApi.qqPlot(
          projectId,
          dataset.id,
          columnName,
          `Q-Q plot — ${labelFor(columnName)}`,
        )
        setPngUrl(url)
      } else if (testKey === 'histogram_normal') {
        const url = await diagnosticsApi.histogram(
          projectId,
          dataset.id,
          columnName,
          `Histogram — ${labelFor(columnName)}`,
        )
        setPngUrl(url)
      } else {
        const res = await diagnosticsApi.run(projectId, dataset.id, {
          test_key: testKey,
          column_name: columnName,
          group_column: needsGroup(testKey) ? groupColumn : null,
        })
        setStatResult(res)
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Diagnostic failed'
      setError(msg)
      toast.error(msg)
    } finally {
      setRunning(false)
    }
  }

  return (
    <div
      className="space-y-4"
      data-testid="diagnostics-panel"
    >
      <div className="rounded-md border border-border bg-muted/20 p-4 space-y-3">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div className="space-y-1.5">
            <Label htmlFor="diag-test">Diagnostic</Label>
            <Select
              value={testKey}
              onValueChange={(v) => setTestKey(v as PickerKey)}
            >
              <SelectTrigger id="diag-test" data-testid="diag-test">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ORDER.map((k) => (
                  <SelectItem key={k} value={k}>
                    {isVisual(k)
                      ? VISUAL_LABELS[k]
                      : DIAGNOSTIC_TEST_LABELS[k]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="diag-col">Column (numeric)</Label>
            <Select
              value={columnName}
              onValueChange={setColumnName}
            >
              <SelectTrigger id="diag-col" data-testid="diag-col">
                <SelectValue placeholder="Pick a numeric column" />
              </SelectTrigger>
              <SelectContent>
                {numericColumns.length === 0 ? (
                  <SelectItem value="__none" disabled>
                    No numeric columns
                  </SelectItem>
                ) : (
                  numericColumns.map((v) => (
                    <SelectItem key={v.id} value={v.name}>
                      {v.display_label?.trim() || v.name}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
          {needsGroup(testKey) && (
            <div className="space-y-1.5">
              <Label htmlFor="diag-group">Group column (nominal)</Label>
              <Select
                value={groupColumn}
                onValueChange={setGroupColumn}
              >
                <SelectTrigger id="diag-group" data-testid="diag-group">
                  <SelectValue placeholder="Pick a group column" />
                </SelectTrigger>
                <SelectContent>
                  {nominalColumns.length === 0 ? (
                    <SelectItem value="__none" disabled>
                      No nominal columns
                    </SelectItem>
                  ) : (
                    nominalColumns.map((v) => (
                      <SelectItem key={v.id} value={v.name}>
                        {v.display_label?.trim() || v.name}
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>
        {error && (
          <div
            className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-[12px] text-rose-800"
            role="alert"
          >
            {error}
          </div>
        )}
        <Button
          type="button"
          onClick={onRun}
          disabled={running}
          className="bg-accent hover:bg-accent-hover text-white"
          data-testid="diag-run"
        >
          {running ? (
            <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
          ) : (
            <FlaskConical className="h-4 w-4 mr-1.5" />
          )}
          Run
        </Button>
      </div>

      {statResult && <StatResultCard result={statResult} />}
      {pngUrl && (
        <div
          className="rounded-md border border-border bg-white overflow-hidden"
          data-testid="diag-png"
        >
          <img
            src={pngUrl}
            alt="Diagnostic plot"
            className="w-full h-auto"
          />
        </div>
      )}
    </div>
  )
}

function StatResultCard({ result }: { result: DiagnosticResult }) {
  const pTxt = formatP(result.p)
  const label =
    DIAGNOSTIC_TEST_LABELS[result.test_key] ?? result.test_key
  return (
    <div
      className="rounded-md border border-border bg-white p-4 space-y-3"
      data-testid="diag-result"
    >
      <div className="flex items-center justify-between gap-3">
        <div className="font-medium text-[14px]">{label}</div>
        <span
          className={cn(
            'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium',
            result.ok
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
              : 'border-amber-200 bg-amber-50 text-amber-700',
          )}
          data-testid="diag-result-pill"
        >
          {result.ok ? (
            <CheckCircle2 className="h-3 w-3" />
          ) : (
            <AlertTriangle className="h-3 w-3" />
          )}
          {result.ok ? 'Assumption holds' : 'Assumption violated'}
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3 text-[12px]">
        <div>
          <div className="text-muted-foreground">Statistic</div>
          <div className="tabular-nums font-medium">
            {result.statistic.toFixed(4)}
          </div>
        </div>
        <div>
          <div className="text-muted-foreground">p-value</div>
          <div className="tabular-nums font-medium">{pTxt}</div>
        </div>
        <div>
          <div className="text-muted-foreground">n</div>
          <div className="tabular-nums font-medium">{result.n}</div>
        </div>
      </div>
      {result.critical_values && (
        <div className="text-[11px] text-muted-foreground">
          Critical values:{' '}
          {Object.entries(result.critical_values)
            .map(([k, v]) => `${k} = ${v.toFixed(3)}`)
            .join(' · ')}
        </div>
      )}
      <p className="text-[13px] leading-relaxed">{result.interpretation}</p>
    </div>
  )
}
