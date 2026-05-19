/**
 * Phase 13.5 (MP13.5) — Analysis plan runner.
 *
 * Pick a plan + a dataset, click Run, see the per-step roll-up. The
 * plan-runner service tags each step ``ok`` or ``failed`` and the run's
 * status is ``ok`` (all green), ``partial`` (some failed), or ``failed``
 * (could not load the dataset at all). The runner does NOT abort on a
 * single bad step.
 */
import { CheckCircle2, Loader2, Play, XCircle } from 'lucide-react'
import { useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import type {
  AnalysisPlanRead,
  AnalysisPlanRunRead,
  Dataset,
  PlanRunStatus,
} from '@/lib/api'
import {
  useAnalysisPlanRuns,
  useAnalysisPlans,
  useRunAnalysisPlan,
} from '@/hooks/useAnalysisPlans'

const STATUS_TONE: Record<PlanRunStatus, string> = {
  ok: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  partial: 'bg-amber-50 text-amber-700 border-amber-200',
  failed: 'bg-rose-50 text-rose-700 border-rose-200',
}

export function AnalysisPlanRunner({
  projectId,
  datasets,
}: {
  projectId: string
  datasets: Dataset[]
}) {
  const { data: plans = [], isLoading: plansLoading } = useAnalysisPlans(projectId)
  const [planId, setPlanId] = useState<string>('')
  const [datasetId, setDatasetId] = useState<string>('')
  const run = useRunAnalysisPlan(projectId)

  const selectedPlan = useMemo(
    () => plans.find((p) => p.id === planId) ?? null,
    [plans, planId],
  )

  const { data: runs = [] } = useAnalysisPlanRuns(
    projectId,
    selectedPlan?.id,
  )

  function handleRun() {
    if (!planId || !datasetId) {
      toast.error('Pick a plan and a dataset.')
      return
    }
    run.mutate(
      { planId, datasetId },
      {
        onSuccess: (r) =>
          toast.success(
            r.status === 'ok'
              ? 'Plan ran successfully.'
              : r.status === 'partial'
              ? 'Plan finished with some failed steps.'
              : 'Plan failed.',
          ),
        onError: (e: Error) => toast.error(e.message),
      },
    )
  }

  return (
    <div className="space-y-4" data-testid="analysis-plan-runner">
      <div className="rounded-lg border border-border bg-white p-4 space-y-3">
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Run a plan
        </div>
        <div className="grid grid-cols-1 md:grid-cols-[1fr_1fr_auto] gap-3 items-end">
          <div>
            <Label htmlFor="run-plan">Plan</Label>
            <Select
              value={planId}
              onValueChange={setPlanId}
              disabled={plansLoading || plans.length === 0}
            >
              <SelectTrigger id="run-plan" data-testid="run-plan">
                <SelectValue placeholder="Pick a plan" />
              </SelectTrigger>
              <SelectContent>
                {plans.map((p) => (
                  <SelectItem key={p.id} value={p.id}>
                    {p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label htmlFor="run-dataset">Dataset</Label>
            <Select
              value={datasetId}
              onValueChange={setDatasetId}
              disabled={datasets.length === 0}
            >
              <SelectTrigger id="run-dataset" data-testid="run-dataset">
                <SelectValue placeholder="Pick a dataset" />
              </SelectTrigger>
              <SelectContent>
                {datasets.map((d) => (
                  <SelectItem key={d.id} value={d.id}>
                    {d.filename}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            onClick={handleRun}
            disabled={run.isPending}
            className="bg-accent hover:bg-accent-hover text-white"
            data-testid="run-plan-go"
          >
            {run.isPending ? (
              <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-1.5" />
            )}
            Run
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Recent runs ({runs.length})
        </div>
        {plansLoading ? (
          <Skeleton className="h-[120px] rounded-md" />
        ) : runs.length === 0 ? (
          <div className="rounded-md border border-dashed border-border bg-white/40 p-4 text-center text-[12px] text-muted-foreground">
            No runs yet.
          </div>
        ) : (
          <ul className="space-y-2">
            {runs.map((r) => (
              <RunCard key={r.id} run={r} />
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function RunCard({ run }: { run: AnalysisPlanRunRead }) {
  const steps = useMemo(() => {
    const blob = run.result_blob as { steps?: unknown[] } | null
    const raw = (blob?.steps as unknown[] | undefined) ?? []
    return raw as Array<{
      step_index: number
      type: string
      status: 'ok' | 'failed'
      error?: string | null
      output?: Record<string, unknown>
    }>
  }, [run])

  return (
    <li
      className="rounded-md border border-border bg-white p-3 space-y-2"
      data-testid={`run-row-${run.id}`}
    >
      <header className="flex items-center justify-between gap-3">
        <div className="text-[12px] text-muted-foreground">
          {new Date(run.executed_at).toLocaleString()}
        </div>
        <Badge variant="outline" className={`text-[11px] ${STATUS_TONE[run.status]}`}>
          {run.status}
        </Badge>
      </header>
      {run.error && (
        <div className="rounded border border-rose-200 bg-rose-50 px-2.5 py-1.5 text-[12px] text-rose-800">
          {run.error}
        </div>
      )}
      <ul className="space-y-1">
        {steps.map((s) => (
          <li
            key={s.step_index}
            className="flex items-start gap-2 text-[12px]"
          >
            {s.status === 'ok' ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <XCircle className="h-3.5 w-3.5 text-rose-600 shrink-0 mt-0.5" />
            )}
            <span className="font-medium">{s.type}</span>
            <span className="text-muted-foreground truncate">
              {s.error ?? JSON.stringify(s.output ?? {})}
            </span>
          </li>
        ))}
      </ul>
    </li>
  )
}
