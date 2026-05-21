/**
 * Phase M4.5 — Page 5 of the mobile Statistics wizard.
 *
 * Route: ``/m/stats/:datasetId/results/:analysisId``.
 *
 * Renders the analysis as a stack of full-width cards:
 *   - Headline statistic card (main p-value, secondary effect size).
 *   - AI interpretation card (prose from the existing interpret
 *     endpoint — already triggered by the configure page).
 *   - Detail tables card (collapsible, the full summary dict).
 *   - Assumptions card (collapsible, only when the runner produced
 *     assumption test results).
 *
 * Bottom action bar:
 *   - "Save name" — opens a sheet so the user can give the analysis a
 *     friendly name. We don't have a backend endpoint for renaming
 *     analyses on mobile, so this is a UI-only stub that uses
 *     localStorage. The desktop app exposes a proper rename.
 *   - "Push to manuscript" — calls the existing push endpoint, which
 *     appends the AI interpretation to the project's Results section.
 *     The Methods / Discussion choices on the sheet are surfaced for
 *     parity with the desktop UX but currently all route to Results
 *     (the backend's behaviour). A toast nudges the user to the
 *     desktop app if they want to drop the result into a different
 *     section.
 *   - "Open in desktop" — for advanced post-hoc work, mirrors the
 *     hint pattern from page 3.
 */
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  ChevronDown,
  ChevronUp,
  FileText,
  Info,
  Loader2,
  Monitor,
  Save,
  Send,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  analysesApi,
  projectsApi,
  TEST_LABELS,
} from '@/lib/api'
import { useLastViewedProject } from '@/lib/projectContext'
import { cn } from '@/lib/utils'

import { BottomSheet } from '../components/BottomSheet'
import { MobileHeader } from '../components/MobileHeader'

type ManuscriptTarget = 'Methods' | 'Results' | 'Discussion'

export default function MobileStatsResults() {
  const navigate = useNavigate()
  const { datasetId, analysisId } = useParams<{
    datasetId: string
    analysisId: string
  }>()
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

  const analysis = useQuery({
    queryKey: ['mstats', 'analysis', activeProjectId, analysisId],
    queryFn: () => analysesApi.get(activeProjectId!, analysisId!),
    enabled: !!activeProjectId && !!analysisId,
    staleTime: 15_000,
  })

  const [showDetails, setShowDetails] = useState(false)
  const [showAssumptions, setShowAssumptions] = useState(false)
  const [pushSheet, setPushSheet] = useState(false)
  const [saveSheet, setSaveSheet] = useState(false)
  const [nameDraft, setNameDraft] = useState('')

  const push = useMutation({
    mutationFn: async (_target: ManuscriptTarget) => {
      if (!activeProjectId || !analysisId) {
        throw new Error('Missing analysis context')
      }
      return analysesApi.pushToManuscript(activeProjectId, analysisId)
    },
    onSuccess: (_resp, target) => {
      toast.success(`Pushed to ${target}`)
      if (target !== 'Results') {
        toast.message(
          'Heads-up: the backend currently appends to Results. Open in desktop to move the paragraph.',
        )
      }
      setPushSheet(false)
    },
    onError: (err) => {
      toast.error(err instanceof Error ? err.message : 'Push failed')
    },
  })

  const result = analysis.data?.result ?? null
  const summary = (result?.summary ?? {}) as Record<string, unknown>
  const assumptions = (result?.assumptions ?? {}) as Record<string, unknown>
  const aiText = result?.ai_interpretation ?? null
  const testLabel = analysis.data
    ? TEST_LABELS[analysis.data.chosen_test]
    : 'Analysis'

  const headlineP = pickHeadline(summary, [
    'p_value',
    'p',
    'p-value',
    'pvalue',
  ])
  const headlineEffect = pickHeadline(summary, [
    'effect_size',
    'cohens_d',
    'estimate',
    'r',
    'rho',
    'odds_ratio',
    'hazard_ratio',
  ])
  const ci = pickCI(summary)

  function onSaveName() {
    if (!analysisId) return
    const key = `mstats:name:${analysisId}`
    if (nameDraft.trim()) {
      window.localStorage?.setItem(key, nameDraft.trim())
      toast.success('Name saved')
    }
    setSaveSheet(false)
  }

  return (
    <div className="flex min-h-full flex-col bg-background pb-32">
      <MobileHeader
        title="Results"
        onBack={() =>
          navigate(`/m/stats/${datasetId}/pick-analysis`)
        }
      />

      {analysis.isLoading && (
        <div
          data-testid="mstats-results-loading"
          className="px-4 py-8 text-center text-[13px] text-muted-foreground"
        >
          Loading results…
        </div>
      )}

      {analysis.data && (
        <div className="space-y-3 px-3 pt-3" data-testid="mstats-results-body">
          {/* Headline card */}
          <div
            data-testid="mstats-headline-card"
            className="rounded-2xl border border-border bg-card px-4 py-5"
          >
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              {testLabel}
            </div>
            <div className="mt-3 flex items-baseline justify-between gap-3">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                  p-value
                </div>
                <div
                  data-testid="mstats-headline-p"
                  className="mt-0.5 text-3xl font-semibold tracking-tight"
                >
                  {headlineP ?? '—'}
                </div>
              </div>
              <div className="text-right">
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
                  effect
                </div>
                <div
                  data-testid="mstats-headline-effect"
                  className="mt-0.5 text-xl font-semibold tracking-tight"
                >
                  {headlineEffect ?? '—'}
                </div>
                {ci && (
                  <div className="mt-1 text-[11px] text-muted-foreground">
                    {ci}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Interpretation card */}
          {aiText && (
            <div
              data-testid="mstats-interpret-card"
              className="rounded-2xl border border-border bg-card px-4 py-4"
            >
              <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                Interpretation
              </div>
              <p className="mt-2 text-[13px] leading-relaxed">
                {stripCitations(aiText)}
              </p>
            </div>
          )}

          {/* Detail tables card */}
          <CollapsibleCard
            testId="mstats-details-card"
            icon={FileText}
            title="Detail tables"
            open={showDetails}
            onToggle={() => setShowDetails((v) => !v)}
          >
            <KeyValueTable data={summary} />
          </CollapsibleCard>

          {/* Assumptions card */}
          {Object.keys(assumptions).length > 0 && (
            <CollapsibleCard
              testId="mstats-assumptions-card"
              icon={Info}
              title="Assumptions"
              open={showAssumptions}
              onToggle={() => setShowAssumptions((v) => !v)}
            >
              <KeyValueTable data={assumptions} />
            </CollapsibleCard>
          )}
        </div>
      )}

      {/* Bottom action bar */}
      <div
        className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-background/95 px-3 py-3 backdrop-blur"
        style={{ paddingBottom: 'calc(12px + env(safe-area-inset-bottom))' }}
      >
        <div className="grid grid-cols-3 gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => setSaveSheet(true)}
            data-testid="mstats-results-save"
          >
            <Save className="mr-1 h-4 w-4" />
            Save
          </Button>
          <Button
            type="button"
            onClick={() => setPushSheet(true)}
            data-testid="mstats-results-push"
            disabled={!aiText}
          >
            <Send className="mr-1 h-4 w-4" />
            Push
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              toast.info(
                'Open this project on the desktop app for advanced post-hoc analyses.',
              )
            }
            data-testid="mstats-results-desktop"
          >
            <Monitor className="mr-1 h-4 w-4" />
            Desktop
          </Button>
        </div>
      </div>

      {/* Push-to-manuscript sheet */}
      <BottomSheet
        open={pushSheet}
        onClose={() => setPushSheet(false)}
        title="Push to manuscript"
        snapPoints={['45%']}
      >
        <div className="space-y-2 pb-2">
          {(['Methods', 'Results', 'Discussion'] as const).map((section) => (
            <button
              key={section}
              type="button"
              data-testid={`mstats-push-${section.toLowerCase()}`}
              onClick={() => push.mutate(section)}
              disabled={push.isPending}
              className={cn(
                'flex w-full items-center justify-between rounded-xl border border-border bg-card px-4 py-3 text-left transition-colors active:bg-muted/60 hover:bg-muted/40',
                push.isPending && 'opacity-60',
              )}
            >
              <div>
                <div className="text-[14px] font-semibold leading-tight">
                  {section}
                </div>
                <div className="mt-0.5 text-[12px] text-muted-foreground">
                  {section === 'Results'
                    ? 'Append the interpretation to the Results section.'
                    : `Push to ${section} (currently routed to Results — edit on desktop).`}
                </div>
              </div>
              {push.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              ) : null}
            </button>
          ))}
        </div>
      </BottomSheet>

      {/* Save-name sheet */}
      <BottomSheet
        open={saveSheet}
        onClose={() => setSaveSheet(false)}
        title="Rename analysis"
        snapPoints={['40%']}
      >
        <div className="flex flex-col gap-3 pb-2">
          <label
            className="text-[12px] text-muted-foreground"
            htmlFor="mstats-name-input"
          >
            Friendly name (saved locally on this device)
          </label>
          <input
            id="mstats-name-input"
            data-testid="mstats-name-input"
            type="text"
            value={nameDraft}
            onChange={(e) => setNameDraft(e.target.value)}
            placeholder={testLabel}
            className="h-11 rounded-lg border border-border bg-card px-3 text-[14px] focus:outline-none focus:ring-2 focus:ring-primary/40"
          />
          <Button
            type="button"
            data-testid="mstats-name-submit"
            onClick={onSaveName}
          >
            Save name
          </Button>
        </div>
      </BottomSheet>
    </div>
  )
}

function CollapsibleCard({
  testId,
  icon: Icon,
  title,
  open,
  onToggle,
  children,
}: {
  testId: string
  icon: typeof FileText
  title: string
  open: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <div
      data-testid={testId}
      className="rounded-2xl border border-border bg-card"
    >
      <button
        type="button"
        onClick={onToggle}
        data-testid={`${testId}-toggle`}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-muted-foreground" />
          <span className="text-[14px] font-medium">{title}</span>
        </div>
        {open ? (
          <ChevronUp className="h-4 w-4 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        )}
      </button>
      {open && (
        <div className="border-t border-border px-4 py-3 text-[13px]">
          {children}
        </div>
      )}
    </div>
  )
}

function KeyValueTable({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data)
  if (entries.length === 0) {
    return <div className="text-muted-foreground text-[12px]">No values</div>
  }
  return (
    <dl className="divide-y divide-border">
      {entries.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3 py-1.5">
          <dt className="text-[12px] uppercase tracking-wider text-muted-foreground">
            {k}
          </dt>
          <dd className="truncate text-[12px] font-medium">
            {formatValue(v)}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function formatValue(v: unknown): string {
  if (v == null) return '—'
  if (typeof v === 'number') {
    if (Math.abs(v) < 1e-4 && v !== 0) return v.toExponential(2)
    return v.toFixed(Math.abs(v) >= 100 ? 1 : 3).replace(/\.?0+$/, '')
  }
  if (typeof v === 'string') return v
  if (Array.isArray(v)) return v.map(formatValue).join(', ')
  return JSON.stringify(v)
}

/**
 * Strip ``[CITE_…]`` tokens out of the AI interpretation so the mobile
 * card never shows a raw token. The desktop manuscript editor resolves
 * these to formatted citations; on mobile we just drop them.
 */
function stripCitations(text: string): string {
  return text.replace(/\[CITE_[^\]]+\]/g, '').replace(/\s{2,}/g, ' ').trim()
}

function pickHeadline(
  summary: Record<string, unknown>,
  keys: string[],
): string | null {
  for (const k of keys) {
    if (k in summary) {
      const v = summary[k]
      if (typeof v === 'number') return formatValue(v)
      if (typeof v === 'string') return v
    }
  }
  return null
}

function pickCI(summary: Record<string, unknown>): string | null {
  const lo = summary.ci_lower ?? summary.ci_low ?? summary.lower
  const hi = summary.ci_upper ?? summary.ci_high ?? summary.upper
  if (typeof lo === 'number' && typeof hi === 'number') {
    return `95% CI ${formatValue(lo)} to ${formatValue(hi)}`
  }
  return null
}
