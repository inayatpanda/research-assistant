/**
 * Phase M4.4 — Page 4 of the mobile Statistics wizard.
 *
 * Route: ``/m/stats/:datasetId/configure/:analysisType``.
 *
 * A small form whose inputs depend on the analysis type. Every
 * column-picker input is a tappable row that opens a ``BottomSheet``
 * listing the dataset's columns, filtered down to the columns that
 * make sense for that role (numeric outcome for a t-test, etc.).
 *
 * On "Run", we POST to the existing
 * ``/api/projects/:pid/datasets/:dsId/analyses`` endpoint with the
 * triple ``{question_type, chosen_test, variables}`` (mirrors the
 * desktop wizard's payload), then ``/run`` and ``/interpret`` so the
 * results page can render immediately without a follow-up tap. Errors
 * surface as toasts; the bottom action bar stays sticky.
 *
 * Mobile keeps the catalogue deliberately small — heavy work (mixed-
 * effects, PSM) stays desktop-only — so this single form covers all
 * seven analysis types via a switch on ``analysisType``.
 */
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  ArrowRight,
  ChevronDown,
  Loader2,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  analysesApi,
  datasetsApi,
  projectsApi,
  type DatasetVariable,
  type VariableType,
} from '@/lib/api'
import { useLastViewedProject } from '@/lib/projectContext'
import { cn } from '@/lib/utils'

import { BottomSheet } from '../components/BottomSheet'
import { MobileHeader } from '../components/MobileHeader'
import {
  buildPayload,
  filterByType,
  findAnalysis,
  validateConfigure,
  variableLabel,
  type ConfigureState,
  type MobileAnalysisType,
} from '../lib/statsWizard'

/** Role-name → allowed variable types for the column picker. */
function allowedTypes(
  analysis: MobileAnalysisType,
  role: keyof ConfigureState,
): VariableType[] {
  if (analysis === 'chi_square') return ['nominal', 'ordinal']
  if (analysis === 't_test' || analysis === 'anova') {
    if (role === 'outcome') return ['numeric', 'ordinal']
    if (role === 'groups') return ['nominal', 'ordinal']
  }
  if (analysis === 'correlation') return ['numeric', 'ordinal']
  if (analysis === 'linear_reg') {
    if (role === 'outcome') return ['numeric']
    if (role === 'predictors') return ['numeric', 'nominal', 'ordinal']
  }
  if (analysis === 'logistic_reg') {
    if (role === 'outcome') return ['nominal', 'ordinal', 'event_indicator']
    if (role === 'predictors') return ['numeric', 'nominal', 'ordinal']
  }
  if (analysis === 'survival') {
    if (role === 'time') return ['numeric', 'time']
    if (role === 'event') return ['event_indicator', 'nominal']
  }
  return ['numeric', 'nominal', 'ordinal', 'time', 'event_indicator']
}

export default function MobileStatsConfigure() {
  const navigate = useNavigate()
  const { datasetId, analysisType } = useParams<{
    datasetId: string
    analysisType: string
  }>()
  const lastProjectId = useLastViewedProject((s) => s.projectId)

  const entry = findAnalysis(analysisType)

  const projects = useQuery({
    queryKey: ['projects', 'list'],
    queryFn: () => projectsApi.list(),
    staleTime: 60_000,
  })

  const activeProjectId = useMemo(() => {
    const list = projects.data ?? []
    if (list.length === 0) return null
    const valid = lastProjectId && list.some((p) => p.id === lastProjectId)
    return valid ? lastProjectId : list[0]?.id ?? null
  }, [projects.data, lastProjectId])

  const dataset = useQuery({
    queryKey: ['mstats', 'dataset', activeProjectId, datasetId],
    queryFn: () => datasetsApi.get(activeProjectId!, datasetId!),
    enabled: !!activeProjectId && !!datasetId,
    staleTime: 30_000,
  })

  const [state, setState] = useState<ConfigureState>({})
  const [pickerRole, setPickerRole] = useState<{
    role: keyof ConfigureState
    multi: boolean
  } | null>(null)

  const variables = dataset.data?.variables ?? []

  const run = useMutation({
    mutationFn: async () => {
      if (!entry || !activeProjectId || !datasetId) {
        throw new Error('Analysis is not configured')
      }
      const validation = validateConfigure(entry.type, state)
      if (validation) throw new Error(validation)
      const payload = buildPayload(entry, state)
      const created = await analysesApi.create(activeProjectId, datasetId, payload)
      const ran = await analysesApi.run(activeProjectId, created.id)
      // Best-effort interpretation — failures don't block navigation.
      try {
        await analysesApi.interpret(activeProjectId, ran.id)
      } catch (err) {
        toast.warning(
          `Ran without AI interpretation: ${
            err instanceof Error ? err.message : String(err)
          }`,
        )
      }
      return ran
    },
    onSuccess: (analysis) => {
      navigate(`/m/stats/${datasetId}/results/${analysis.id}`)
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Failed to run analysis')
    },
  })

  if (!entry) {
    return (
      <div className="flex min-h-full flex-col bg-background">
        <MobileHeader
          title="Configure"
          onBack={() => navigate(`/m/stats/${datasetId}/pick-analysis`)}
        />
        <div
          data-testid="mstats-configure-unknown"
          className="px-4 py-8 text-[13px] text-muted-foreground"
        >
          Unknown analysis type. Go back and pick one from the list.
        </div>
      </div>
    )
  }

  function setPickerOpen(role: keyof ConfigureState, multi = false) {
    setPickerRole({ role, multi })
  }

  function pickColumn(name: string) {
    if (!pickerRole) return
    const { role, multi } = pickerRole
    if (multi) {
      const current = (state[role] as string[] | undefined) ?? []
      const next = current.includes(name)
        ? current.filter((c) => c !== name)
        : [...current, name]
      setState({ ...state, [role]: next })
    } else {
      setState({ ...state, [role]: name })
      setPickerRole(null)
    }
  }

  const allowed = pickerRole
    ? allowedTypes(entry.type, pickerRole.role)
    : []
  const pickerColumns: DatasetVariable[] = pickerRole
    ? filterByType(variables, allowed)
    : []
  const selectedPredictors = state.predictors ?? []

  return (
    <div className="flex min-h-full flex-col bg-background pb-32">
      <MobileHeader
        title={entry.title}
        onBack={() => navigate(`/m/stats/${datasetId}/pick-analysis`)}
      />

      <div className="px-3 pt-3" data-testid="mstats-configure-form">
        <p className="px-1 pb-3 text-[12px] text-muted-foreground">
          {entry.blurb}
        </p>

        <div className="space-y-2">
          {(entry.type === 't_test' || entry.type === 'anova') && (
            <>
              <PickerRow
                testId="mstats-pick-outcome"
                label="Outcome"
                value={resolveLabel(variables, state.outcome)}
                onClick={() => setPickerOpen('outcome')}
              />
              <PickerRow
                testId="mstats-pick-groups"
                label="Group"
                value={resolveLabel(variables, state.groups)}
                onClick={() => setPickerOpen('groups')}
              />
            </>
          )}

          {entry.type === 'chi_square' && (
            <>
              <PickerRow
                testId="mstats-pick-outcome"
                label="First categorical"
                value={resolveLabel(variables, state.outcome)}
                onClick={() => setPickerOpen('outcome')}
              />
              <PickerRow
                testId="mstats-pick-groups"
                label="Second categorical"
                value={resolveLabel(variables, state.groups)}
                onClick={() => setPickerOpen('groups')}
              />
            </>
          )}

          {entry.type === 'correlation' && (
            <>
              <PickerRow
                testId="mstats-pick-x"
                label="Variable 1"
                value={resolveLabel(variables, state.x)}
                onClick={() => setPickerOpen('x')}
              />
              <PickerRow
                testId="mstats-pick-y"
                label="Variable 2"
                value={resolveLabel(variables, state.y)}
                onClick={() => setPickerOpen('y')}
              />
              <MethodToggle
                value={state.method ?? 'pearson'}
                onChange={(m) => setState({ ...state, method: m })}
              />
            </>
          )}

          {(entry.type === 'linear_reg' || entry.type === 'logistic_reg') && (
            <>
              <PickerRow
                testId="mstats-pick-outcome"
                label="Outcome"
                value={resolveLabel(variables, state.outcome)}
                onClick={() => setPickerOpen('outcome')}
              />
              <PickerRow
                testId="mstats-pick-predictors"
                label="Predictors"
                value={
                  selectedPredictors.length === 0
                    ? null
                    : selectedPredictors
                        .map((p) => resolveLabel(variables, p) ?? p)
                        .join(', ')
                }
                onClick={() => setPickerOpen('predictors', true)}
              />
            </>
          )}

          {entry.type === 'survival' && (
            <>
              <PickerRow
                testId="mstats-pick-time"
                label="Time"
                value={resolveLabel(variables, state.time)}
                onClick={() => setPickerOpen('time')}
              />
              <PickerRow
                testId="mstats-pick-event"
                label="Event indicator"
                value={resolveLabel(variables, state.event)}
                onClick={() => setPickerOpen('event')}
              />
              <PickerRow
                testId="mstats-pick-strata"
                label="Strata (optional)"
                value={resolveLabel(variables, state.groups)}
                onClick={() => setPickerOpen('groups')}
              />
            </>
          )}
        </div>

        {run.isPending && (
          <div
            data-testid="mstats-running"
            className="mt-6 flex items-center justify-center gap-2 rounded-xl border border-border bg-card px-4 py-4 text-[13px] text-muted-foreground"
          >
            <Loader2 className="h-4 w-4 animate-spin" />
            Running analysis…
          </div>
        )}
      </div>

      {/* Bottom action bar */}
      <div
        className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-background/95 px-3 py-3 backdrop-blur"
        style={{ paddingBottom: 'calc(12px + env(safe-area-inset-bottom))' }}
      >
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            className="flex-1"
            onClick={() => navigate(`/m/stats/${datasetId}/pick-analysis`)}
            data-testid="mstats-configure-back"
          >
            Back
          </Button>
          <Button
            type="button"
            className="flex-1"
            onClick={() => run.mutate()}
            disabled={run.isPending}
            data-testid="mstats-configure-run"
          >
            {run.isPending ? (
              <Loader2 className="mr-1 h-4 w-4 animate-spin" />
            ) : (
              <>
                Run analysis
                <ArrowRight className="ml-1 h-4 w-4" />
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Column picker sheet */}
      <BottomSheet
        open={pickerRole != null}
        onClose={() => setPickerRole(null)}
        title="Pick a column"
        snapPoints={['70%']}
      >
        {pickerRole && pickerColumns.length === 0 && (
          <div
            data-testid="mstats-picker-empty"
            className="py-6 text-center text-[13px] text-muted-foreground"
          >
            No columns match the required type for this role. Go back to the
            preview step and update the column types.
          </div>
        )}
        <div className="space-y-1.5 pb-2">
          {pickerColumns.map((v) => {
            const selected = pickerRole?.multi
              ? selectedPredictors.includes(v.name)
              : (state[pickerRole!.role] as string | undefined) === v.name
            return (
              <button
                key={v.id}
                type="button"
                data-testid={`mstats-picker-${v.name}`}
                onClick={() => pickColumn(v.name)}
                className={cn(
                  'flex w-full items-center justify-between rounded-lg border px-3 py-3 text-left transition-colors',
                  selected
                    ? 'border-primary bg-primary/5'
                    : 'border-border bg-card active:bg-muted/40',
                )}
              >
                <span className="min-w-0">
                  <span className="block text-[14px] font-medium leading-tight">
                    {variableLabel(v)}
                  </span>
                  <span className="mt-0.5 block text-[11px] text-muted-foreground">
                    {v.user_type ?? v.inferred_type}
                  </span>
                </span>
                {selected && (
                  <span className="text-[11px] font-medium text-primary">
                    {pickerRole?.multi ? 'Selected' : '✓'}
                  </span>
                )}
              </button>
            )
          })}
          {pickerRole?.multi && (
            <Button
              type="button"
              className="mt-3 w-full"
              onClick={() => setPickerRole(null)}
              data-testid="mstats-picker-done"
            >
              Done
            </Button>
          )}
        </div>
      </BottomSheet>
    </div>
  )
}

function PickerRow({
  label,
  value,
  onClick,
  testId,
}: {
  label: string
  value: string | null | undefined
  onClick: () => void
  testId: string
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testId}
      className="flex w-full items-center justify-between gap-3 rounded-xl border border-border bg-card px-4 py-3 text-left transition-colors active:bg-muted/60 hover:bg-muted/40"
    >
      <div className="min-w-0">
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          {label}
        </div>
        <div
          className={cn(
            'mt-0.5 truncate text-[14px]',
            value ? 'font-medium' : 'text-muted-foreground',
          )}
        >
          {value ?? 'Choose…'}
        </div>
      </div>
      <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
    </button>
  )
}

function MethodToggle({
  value,
  onChange,
}: {
  value: 'pearson' | 'spearman'
  onChange: (v: 'pearson' | 'spearman') => void
}) {
  return (
    <div className="rounded-xl border border-border bg-card px-4 py-3">
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
        Method
      </div>
      <div className="mt-2 flex gap-2">
        {(['pearson', 'spearman'] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => onChange(m)}
            data-testid={`mstats-method-${m}`}
            className={cn(
              'flex-1 rounded-full border px-3 py-1.5 text-[13px] font-medium',
              value === m
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-card text-muted-foreground',
            )}
          >
            {m === 'pearson' ? 'Pearson' : 'Spearman'}
          </button>
        ))}
      </div>
    </div>
  )
}

function resolveLabel(
  variables: DatasetVariable[],
  name: string | undefined,
): string | null {
  if (!name) return null
  const v = variables.find((vv) => vv.name === name)
  return v ? variableLabel(v) : name
}

