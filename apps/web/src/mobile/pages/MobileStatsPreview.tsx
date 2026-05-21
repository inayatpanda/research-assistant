/**
 * Phase M4.2 — Page 2 of the mobile Statistics wizard.
 *
 * Route: ``/m/stats/:datasetId/preview``.
 *
 * Shows a mini-summary chip row (N rows · M cols · sheet name when
 * present), then a horizontally scrollable mini-table of the first 8
 * rows. Each column header is tappable — opens a ``BottomSheet`` with
 * the variable's display label (editable) + a type radio (Numeric /
 * Categorical / Date / Outcome). The "Outcome" choice is a UI
 * shorthand for "event indicator" which is the backend's preferred
 * type for survival event flags; everything else maps onto the
 * existing ``VariableType`` enum.
 *
 * AI auto-suggestions: the dataset's variables already carry an
 * ``inferred_type`` from the backend (assigned at upload time). We
 * surface a small "AI suggested" badge on columns whose ``user_type``
 * is still null — i.e. the user hasn't reviewed the inference yet.
 *
 * Bottom action bar: "Back" + "Continue to analysis". Continue is
 * enabled when at least one variable carries a ``user_type``.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Loader2, Sparkles } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  datasetsApi,
  projectsApi,
  type DatasetVariable,
  type VariableType,
} from '@/lib/api'
import { useLastViewedProject } from '@/lib/projectContext'
import { cn } from '@/lib/utils'

import { BottomSheet } from '../components/BottomSheet'
import { MobileHeader } from '../components/MobileHeader'

import { effectiveType, variableLabel } from '../lib/statsWizard'

const TYPE_RADIO: Array<{
  key: VariableType
  label: string
  blurb: string
}> = [
  {
    key: 'numeric',
    label: 'Numeric',
    blurb: 'Continuous measurement (e.g. weight, length, score).',
  },
  {
    key: 'nominal',
    label: 'Categorical',
    blurb: 'Discrete groups (e.g. sex, treatment arm).',
  },
  {
    key: 'time',
    label: 'Date / time',
    blurb: 'Date, datetime or time-to-event.',
  },
  {
    key: 'event_indicator',
    label: 'Outcome',
    blurb: '0/1 event flag for survival or logistic models.',
  },
]

const PREVIEW_ROWS = 8

export default function MobileStatsPreview() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { datasetId } = useParams<{ datasetId: string }>()
  const lastProjectId = useLastViewedProject((s) => s.projectId)

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

  const preview = useQuery({
    queryKey: ['mstats', 'preview', activeProjectId, datasetId],
    queryFn: () =>
      datasetsApi.preview(activeProjectId!, datasetId!, 0, PREVIEW_ROWS),
    enabled: !!activeProjectId && !!datasetId,
    staleTime: 30_000,
  })

  const [editing, setEditing] = useState<DatasetVariable | null>(null)
  const [labelDraft, setLabelDraft] = useState('')
  const [typeDraft, setTypeDraft] = useState<VariableType>('unknown')

  const updateType = useMutation({
    mutationFn: async (args: {
      variableId: string
      type: VariableType
    }) => {
      return datasetsApi.updateVariable(
        activeProjectId!,
        datasetId!,
        args.variableId,
        args.type,
      )
    },
  })

  const updateLabel = useMutation({
    mutationFn: async (args: { variableId: string; label: string }) => {
      return datasetsApi.updateVariableDisplayLabel(
        activeProjectId!,
        datasetId!,
        args.variableId,
        args.label,
      )
    },
  })

  function openColumnSheet(v: DatasetVariable) {
    setEditing(v)
    setLabelDraft(v.display_label ?? v.name)
    setTypeDraft(v.user_type ?? v.inferred_type)
  }

  async function saveColumn() {
    if (!editing) return
    const id = editing.id
    try {
      // Save label first so the dataset payload sees the new label on
      // refetch.
      if (labelDraft.trim() && labelDraft !== (editing.display_label ?? editing.name)) {
        await updateLabel.mutateAsync({ variableId: id, label: labelDraft.trim() })
      }
      if (typeDraft !== (editing.user_type ?? 'unknown')) {
        await updateType.mutateAsync({ variableId: id, type: typeDraft })
      }
      qc.invalidateQueries({
        queryKey: ['mstats', 'dataset', activeProjectId, datasetId],
      })
      toast.success('Column saved')
      setEditing(null)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to save column')
    }
  }

  const variables = dataset.data?.variables ?? []
  const hasReviewed = variables.some((v) => v.user_type != null)
  const sheetName =
    (dataset.data?.dataset_metadata?.sheet_name as string | undefined) ?? null

  return (
    <div className="flex min-h-full flex-col bg-background pb-32">
      <MobileHeader
        title="Preview & column types"
        onBack={() => navigate('/m/stats')}
      />

      {/* Summary chip row */}
      <div className="flex flex-wrap gap-2 px-4 pt-3 pb-2 text-[12px] text-muted-foreground">
        {dataset.isLoading ? (
          <span data-testid="mstats-preview-loading">Loading…</span>
        ) : dataset.data ? (
          <>
            <SummaryChip
              testId="mstats-summary-rows"
              label={`${dataset.data.n_rows.toLocaleString()} rows`}
            />
            <SummaryChip
              testId="mstats-summary-cols"
              label={`${dataset.data.n_columns} cols`}
            />
            {sheetName && (
              <SummaryChip
                testId="mstats-summary-sheet"
                label={`sheet: ${sheetName}`}
              />
            )}
          </>
        ) : null}
      </div>

      {/* Mini-table */}
      <div className="px-3 pt-2">
        {!dataset.isLoading && variables.length > 0 && (
          <div
            data-testid="mstats-preview-table"
            className="overflow-x-auto rounded-xl border border-border bg-card"
          >
            <table className="min-w-full border-collapse text-[12px]">
              <thead className="sticky top-0 z-10 bg-muted/60 backdrop-blur">
                <tr>
                  {variables.map((v) => (
                    <th
                      key={v.id}
                      className="border-b border-border px-3 py-2 text-left whitespace-nowrap"
                    >
                      <button
                        type="button"
                        onClick={() => openColumnSheet(v)}
                        data-testid={`mstats-col-${v.id}`}
                        className="flex flex-col items-start gap-1"
                      >
                        <span className="font-semibold tracking-tight">
                          {variableLabel(v)}
                        </span>
                        <span className="flex items-center gap-1">
                          <TypeBadge type={effectiveType(v)} />
                          {v.user_type == null && (
                            <span
                              data-testid={`mstats-col-${v.id}-ai-badge`}
                              className="inline-flex items-center gap-0.5 rounded-full bg-primary/10 px-1.5 py-px text-[10px] font-medium text-primary"
                            >
                              <Sparkles className="h-2.5 w-2.5" />
                              AI
                            </span>
                          )}
                        </span>
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(preview.data?.rows ?? []).map((row, ri) => (
                  <tr key={ri} className="border-b border-border last:border-b-0">
                    {variables.map((v) => (
                      <td
                        key={v.id}
                        className="px-3 py-2 align-top text-muted-foreground whitespace-nowrap"
                      >
                        {String((row as Record<string, unknown>)[v.name] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
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
            onClick={() => navigate('/m/stats')}
            data-testid="mstats-preview-back"
          >
            Back
          </Button>
          <Button
            type="button"
            className="flex-1"
            disabled={!hasReviewed}
            onClick={() => navigate(`/m/stats/${datasetId}/pick-analysis`)}
            data-testid="mstats-preview-continue"
          >
            Continue
            <ArrowRight className="ml-1 h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Column type sheet */}
      <BottomSheet
        open={editing != null}
        onClose={() => setEditing(null)}
        title="Column settings"
        snapPoints={['65%']}
      >
        {editing && (
          <div className="flex flex-col gap-4 pb-2">
            <div>
              <label
                className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium"
                htmlFor="mstats-col-label"
              >
                Display label
              </label>
              <input
                id="mstats-col-label"
                data-testid="mstats-col-label-input"
                type="text"
                value={labelDraft}
                onChange={(e) => setLabelDraft(e.target.value)}
                className="mt-1.5 h-11 w-full rounded-lg border border-border bg-card px-3 text-[14px] focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
              <div className="mt-1 text-[11px] text-muted-foreground">
                Original column name: <code>{editing.name}</code>
              </div>
            </div>

            <div>
              <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                Type
              </div>
              <div className="mt-2 space-y-1.5">
                {TYPE_RADIO.map((opt) => (
                  <button
                    key={opt.key}
                    type="button"
                    onClick={() => setTypeDraft(opt.key)}
                    data-testid={`mstats-col-type-${opt.key}`}
                    className={cn(
                      'flex w-full items-start gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors',
                      typeDraft === opt.key
                        ? 'border-primary bg-primary/5'
                        : 'border-border bg-card hover:bg-muted/40',
                    )}
                  >
                    <span
                      className={cn(
                        'mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2',
                        typeDraft === opt.key
                          ? 'border-primary'
                          : 'border-muted-foreground/50',
                      )}
                    >
                      {typeDraft === opt.key && (
                        <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                      )}
                    </span>
                    <span className="min-w-0">
                      <span className="block text-[14px] font-medium">
                        {opt.label}
                      </span>
                      <span className="mt-0.5 block text-[12px] text-muted-foreground">
                        {opt.blurb}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <Button
              type="button"
              data-testid="mstats-col-save"
              onClick={saveColumn}
              disabled={updateType.isPending || updateLabel.isPending}
            >
              {updateType.isPending || updateLabel.isPending ? (
                <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
              ) : null}
              Save
            </Button>
          </div>
        )}
      </BottomSheet>
    </div>
  )
}

function SummaryChip({
  testId,
  label,
}: {
  testId: string
  label: string
}) {
  return (
    <span
      data-testid={testId}
      className="inline-flex items-center rounded-full border border-border bg-card px-2.5 py-1"
    >
      {label}
    </span>
  )
}

const TYPE_LABEL: Record<VariableType, string> = {
  numeric: 'numeric',
  ordinal: 'ordinal',
  nominal: 'categorical',
  time: 'date',
  event_indicator: 'outcome',
  unknown: 'unknown',
}

function TypeBadge({ type }: { type: VariableType }) {
  return (
    <span className="inline-flex items-center rounded-full bg-muted px-1.5 py-px text-[10px] font-medium text-muted-foreground">
      {TYPE_LABEL[type]}
    </span>
  )
}
