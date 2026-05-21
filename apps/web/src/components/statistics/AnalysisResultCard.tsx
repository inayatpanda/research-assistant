import { motion } from 'framer-motion'
import {
  BookmarkPlus,
  FileSpreadsheet,
  Loader2,
  RefreshCw,
  Send,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { LearnTooltip } from '@/components/learn/LearnTooltip'
import { Button } from '@/components/ui/button'
import {
  TEST_LABELS,
  type Analysis,
  type Dataset,
  type TestKey,
} from '@/lib/api'
import { cn } from '@/lib/utils'

/**
 * Map an analysis test_key to the canonical Learn concept slug. Anything
 * not in the table falls through to the kebab-cased test_key, which the
 * LearnTooltip will gracefully ignore via `isKnownLearnConcept`.
 */
const TEST_LEARN_CONCEPT: Partial<Record<TestKey, string>> = {
  independent_t: 'independent-t-test',
  paired_t: 'paired-t-test',
  mann_whitney: 'mann-whitney-u',
  wilcoxon_signed: 'wilcoxon-signed-rank',
  chi_squared: 'chi-square-independence',
  fisher_exact: 'fisher-exact',
  one_way_anova: 'one-way-anova',
  kruskal_wallis: 'kruskal-wallis',
  rm_anova: 'repeated-measures-anova',
  pearson: 'pearson-correlation',
  spearman: 'spearman-correlation',
  linear_regression: 'linear-regression',
  multiple_linear: 'multiple-linear-regression',
  logistic: 'logistic-regression',
  kaplan_meier: 'kaplan-meier-log-rank',
  cox_ph: 'cox-proportional-hazards',
  icc: 'icc',
  mixed_effects_lm: 'mixed-effects-lm',
}
import {
  useDeleteAnalysis,
  useInterpretAnalysis,
  usePushToManuscript,
} from '@/hooks/useAnalyses'
import { useCreateAnalysisPlan } from '@/hooks/useAnalysisPlans'

import { AssumptionPills } from './AssumptionPills'
import { ChartImage } from './ChartImage'
import { EditChartLabelsDialog } from './EditChartLabelsDialog'
import { OLSDiagnosticsPanel } from './OLSDiagnosticsPanel'

/**
 * DEMO-FIX-C — Build a {canonical → display_label} map from a dataset's
 * variables. Falls back to canonical when no display_label is set.
 */
function buildDisplayLabels(dataset: Dataset): Record<string, string> {
  const out: Record<string, string> = {}
  for (const v of dataset.variables) {
    out[v.name] = v.display_label ?? v.name
  }
  return out
}

export function AnalysisResultCard({
  projectId,
  dataset,
  analysis,
}: {
  projectId: string
  dataset: Dataset
  analysis: Analysis
}) {
  const navigate = useNavigate()
  const interpret = useInterpretAnalysis(projectId, dataset.id)
  const push = usePushToManuscript(projectId)
  const del = useDeleteAnalysis(projectId, dataset.id)
  const savePlan = useCreateAnalysisPlan(projectId)
  const [editLabelsOpen, setEditLabelsOpen] = useState(false)

  const result = analysis.result
  const summary = (result?.summary ?? {}) as Record<string, unknown>
  const aiText = result?.ai_interpretation ?? null

  const hasResult = !!result
  const failed = analysis.status === 'failed'

  // DEMO-FIX-C — Resolve {canonical → display_label} once per render so the
  // header subtitle and citation-prose chip both see the same map.
  const displayLabels = useMemo(() => buildDisplayLabels(dataset), [dataset])
  const chart = (result?.chart ?? {}) as Record<string, unknown>
  const chartOverrides = {
    x_label_override:
      typeof chart.x_label_override === 'string' ? chart.x_label_override : '',
    y_label_override:
      typeof chart.y_label_override === 'string' ? chart.y_label_override : '',
    title_override:
      typeof chart.title_override === 'string' ? chart.title_override : '',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-lg border border-border bg-white p-5 space-y-4"
    >
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium flex items-center gap-1">
            <LearnTooltip
              concept={
                TEST_LEARN_CONCEPT[analysis.chosen_test] ??
                analysis.chosen_test.replace(/_/g, '-')
              }
              iconOnly
              description={`Open Learn entry for ${TEST_LABELS[analysis.chosen_test]}`}
            >
              {TEST_LABELS[analysis.chosen_test]}
            </LearnTooltip>
          </div>
          <div className="mt-0.5 text-[13px] text-muted-foreground truncate">
            {variableSummary(analysis.variables, displayLabels)}
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <StatusBadge status={analysis.status} />
          <Button
            size="icon"
            variant="ghost"
            className="h-7 w-7"
            onClick={() => {
              const name = prompt(
                'Plan name?',
                `${TEST_LABELS[analysis.chosen_test]} workflow`,
              )
              if (!name) return
              savePlan.mutate(
                {
                  name: name.trim(),
                  description: `Saved from analysis ${analysis.id}`,
                  steps: [
                    {
                      type: 'test',
                      args: {
                        test_key: analysis.chosen_test,
                        question_type: analysis.question_type,
                        variables: analysis.variables,
                      },
                    },
                  ],
                },
                {
                  onSuccess: () => toast.success('Saved as plan'),
                  onError: (e: Error) => toast.error(e.message),
                },
              )
            }}
            aria-label="Save as plan"
            data-testid={`save-as-plan-${analysis.id}`}
          >
            <BookmarkPlus className="h-4 w-4 text-muted-foreground" />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className="h-7 w-7"
            onClick={() => {
              if (confirm('Delete this analysis?')) {
                del.mutate(analysis.id, {
                  onSuccess: () => toast.success('Analysis deleted'),
                  onError: (e: Error) => toast.error(e.message),
                })
              }
            }}
            aria-label="Delete analysis"
          >
            <Trash2 className="h-4 w-4 text-muted-foreground" />
          </Button>
        </div>
      </header>

      {failed && (
        <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-[12px] text-rose-800">
          Analysis failed to run. Try changing the variable selection.
        </div>
      )}

      {hasResult && (
        <>
          <NumbersGrid summary={summary} />

          {isChartDict(result?.chart) && (
            <ChartImage
              chart={result!.chart as { format: 'png'; data_uri: string; byte_size: number }}
              alt={`${TEST_LABELS[analysis.chosen_test]} chart`}
              downloadName={`analysis-${analysis.id}-chart`}
              onEditLabels={() => setEditLabelsOpen(true)}
            />
          )}

          <EditChartLabelsDialog
            open={editLabelsOpen}
            onOpenChange={setEditLabelsOpen}
            projectId={projectId}
            datasetId={dataset.id}
            analysisId={analysis.id}
            initial={chartOverrides}
          />

          {(analysis.chosen_test === 'linear_regression' ||
            analysis.chosen_test === 'multiple_linear') && (
            <OLSDiagnosticsPanel chart={result?.chart} />
          )}

          {result?.assumptions && (
            <div className="space-y-1.5">
              <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                Assumptions
              </div>
              <AssumptionPills assumptions={result.assumptions} />
            </div>
          )}

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                AI interpretation
              </div>
              {aiText && (
                <Button
                  size="sm"
                  variant="ghost"
                  className="h-7 text-[12px]"
                  onClick={() =>
                    interpret.mutate(analysis.id, {
                      onSuccess: () => toast.success('Re-interpreted'),
                      onError: (e: Error) => toast.error(e.message),
                    })
                  }
                  disabled={interpret.isPending}
                >
                  {interpret.isPending ? (
                    <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
                  ) : (
                    <RefreshCw className="h-3.5 w-3.5 mr-1" />
                  )}
                  Re-interpret
                </Button>
              )}
            </div>

            {aiText ? (
              <div className="rounded-md border border-border bg-muted/30 px-3 py-3 text-[13px] leading-relaxed">
                <CitationProse text={aiText} dataset={dataset} />
              </div>
            ) : (
              <Button
                size="sm"
                variant="outline"
                className="text-[12px]"
                onClick={() =>
                  interpret.mutate(analysis.id, {
                    onSuccess: () => toast.success('Interpreted'),
                    onError: (e: Error) => toast.error(e.message),
                  })
                }
                disabled={interpret.isPending}
              >
                {interpret.isPending ? (
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                )}
                Interpret with AI
              </Button>
            )}
          </div>

          {aiText && (
            <div className="flex justify-end pt-1">
              <Button
                onClick={() =>
                  push.mutate(analysis.id, {
                    onSuccess: () => {
                      toast.success('Pushed to Manuscript Results')
                      navigate(`/projects/${projectId}/manuscript?section=Results`)
                    },
                    onError: (e: Error) => toast.error(e.message),
                  })
                }
                disabled={push.isPending}
                className="bg-accent hover:bg-accent-hover text-white"
              >
                {push.isPending ? (
                  <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                ) : (
                  <Send className="h-4 w-4 mr-1.5" />
                )}
                Push to Manuscript
              </Button>
            </div>
          )}
        </>
      )}
    </motion.div>
  )
}

function NumbersGrid({ summary }: { summary: Record<string, unknown> }) {
  const statistic = asNumber(summary.statistic)
  const p = asNumber(summary.p_value)
  const effect = asNumber(summary.effect_size)
  const ciLow = asNumber(summary.ci_low)
  const ciHigh = asNumber(summary.ci_high)
  const n = asNumber(summary.n)
  const df = asNumber(summary.df)

  const ci = ciLow !== null && ciHigh !== null
    ? `[${formatNumber(ciLow)}, ${formatNumber(ciHigh)}]`
    : '—'

  return (
    <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <Stat label="Statistic" value={formatNumber(statistic)} />
      <Stat label="p-value" value={formatP(p)} />
      <Stat label="Effect size" value={formatNumber(effect)} />
      <Stat label="95% CI" value={ci} />
      <Stat label="n" value={n !== null ? String(n) : '—'} />
      <Stat label="df" value={df !== null ? formatNumber(df) : '—'} />
    </dl>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-muted/20 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
        {label}
      </div>
      <div className="mt-0.5 text-[13px] font-semibold tabular-nums">{value}</div>
    </div>
  )
}

function StatusBadge({ status }: { status: Analysis['status'] }) {
  const tone =
    status === 'completed'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : status === 'failed'
        ? 'bg-rose-50 text-rose-700 border-rose-200'
        : status === 'running'
          ? 'bg-sky-50 text-sky-700 border-sky-200'
          : 'bg-muted text-muted-foreground border-border'
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium capitalize',
        tone,
      )}
    >
      {status === 'running' && <Loader2 className="h-3 w-3 animate-spin" />}
      {status}
    </span>
  )
}

function CitationProse({ text, dataset }: { text: string; dataset: Dataset }) {
  const token = `[CITE_dataset_${dataset.id}]`
  const parts = text.split(token)
  if (parts.length === 1) {
    return <span>{text}</span>
  }
  return (
    <span>
      {parts.map((part, idx) => (
        <span key={idx}>
          {part}
          {idx < parts.length - 1 && <DatasetChip dataset={dataset} />}
        </span>
      ))}
    </span>
  )
}

function DatasetChip({ dataset }: { dataset: Dataset }) {
  return (
    <span
      className="inline-flex items-center gap-1 rounded-md border border-accent/30 bg-accent/10 px-1.5 py-0.5 text-[11px] font-medium text-accent align-baseline mx-0.5"
      title={`Dataset: ${dataset.filename}`}
    >
      <FileSpreadsheet className="h-3 w-3" />
      {dataset.filename}
    </span>
  )
}

function variableSummary(
  vars: Record<string, unknown>,
  labels: Record<string, string> = {},
): string {
  // DEMO-FIX-C — Resolve canonical column names via the display-label map so
  // the card subtitle reads "outcome: VAS Pain at 6 months (post-op)" instead
  // of "outcome: vas_pain_6m_postop".
  const resolve = (s: string): string => labels[s] ?? s
  return Object.entries(vars)
    .map(([k, v]) => {
      if (Array.isArray(v)) {
        const items = v.map((x) => (typeof x === 'string' ? resolve(x) : String(x)))
        return `${k}: ${items.join(', ')}`
      }
      if (typeof v === 'string') return `${k}: ${resolve(v)}`
      return null
    })
    .filter(Boolean)
    .join(' · ')
}

function isChartDict(
  chart: unknown,
): chart is { format: 'png'; data_uri: string; byte_size: number } {
  if (!chart || typeof chart !== 'object') return false
  const c = chart as Record<string, unknown>
  return (
    c.format === 'png' &&
    typeof c.data_uri === 'string' &&
    c.data_uri.startsWith('data:image/png;base64,')
  )
}

function asNumber(v: unknown): number | null {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  return null
}

function formatNumber(v: number | null): string {
  if (v === null) return '—'
  const abs = Math.abs(v)
  if (abs >= 1000) return v.toFixed(1)
  if (abs >= 1) return v.toFixed(3)
  if (abs === 0) return '0'
  return v.toFixed(3)
}

function formatP(p: number | null): string {
  if (p === null) return '—'
  if (p < 0.001) return '<0.001'
  return p.toFixed(3)
}
