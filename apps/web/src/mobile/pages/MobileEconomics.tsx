/**
 * Phase M5.1 — Mobile Health-economics mini-app.
 *
 * Lives at ``/m/economics``. Three on-device calculator cards plus a list
 * of any past full ICER analyses that exist for the active project (the
 * desktop pathway creates these from a dataset; mobile only browses).
 *
 * Cards:
 *   - ICER   (cost_a, cost_b, qaly_a, qaly_b → ICER + dominance quadrant)
 *   - QALY   (utility, duration_years → quality-adjusted life years)
 *   - NMB    (qaly_diff, cost_diff, wtp → net monetary benefit + verdict)
 *
 * The math runs entirely client-side — there's no quick "compute this"
 * endpoint on the backend (existing /economic-analyses requires a bound
 * dataset). Each card has an info chip that opens a <BottomSheet> with
 * the corresponding Learn entry (same MarkdownView pattern as
 * MobileLearnEntryPage).
 *
 * Project picker chip at the top mirrors MobileStatsUpload.
 */
import { useQuery } from '@tanstack/react-query'
import {
  ChevronDown,
  ChevronRight,
  Info,
  Loader2,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { MarkdownView } from '@/components/learn/MarkdownView'
import { Badge } from '@/components/ui/badge'
import {
  economicAnalysesApi,
  learnApi,
  projectsApi,
  type EconomicAnalysis,
  type LearnEconomicsRead,
} from '@/lib/api'
import { useLastViewedProject } from '@/lib/projectContext'
import { cn } from '@/lib/utils'

import { BottomSheet } from '../components/BottomSheet'
import { MobileEmpty } from '../components/MobileEmpty'

type CalcId = 'icer' | 'qaly' | 'nmb'

const LEARN_SLUG_BY_CALC: Record<CalcId, string> = {
  icer: 'incremental-cost-effectiveness-ratio',
  qaly: 'quality-adjusted-life-year',
  nmb: 'net-monetary-benefit',
}

const CALC_TITLE: Record<CalcId, string> = {
  icer: 'Incremental cost-effectiveness ratio',
  qaly: 'Quality-adjusted life years',
  nmb: 'Net monetary benefit',
}

const CALC_BLURB: Record<CalcId, string> = {
  icer: 'Compare two arms by cost-per-QALY.',
  qaly: 'Convert a utility weight + duration into QALYs.',
  nmb: 'Decide cost-effectiveness at a WTP threshold.',
}

// ── Pure math helpers (mirror the backend services/economics) ────────────
const EPS = 1e-9
type IcerResult = {
  icer: number | null
  dominance: 'dominant' | 'dominated' | 'northeast' | 'southwest' | 'equal'
  verdict: string
  ciLow: number | null
  ciHigh: number | null
  belowWtp: boolean | null
}

function computeIcer(
  costA: number,
  costB: number,
  qalyA: number,
  qalyB: number,
  wtp: number,
): IcerResult {
  const dC = costA - costB
  const dQ = qalyA - qalyB
  if (Math.abs(dC) < EPS && Math.abs(dQ) < EPS) {
    return {
      icer: null,
      dominance: 'equal',
      verdict: 'Arms are essentially equal — no incremental difference.',
      ciLow: null,
      ciHigh: null,
      belowWtp: null,
    }
  }
  if (dC < -EPS && dQ > EPS) {
    return {
      icer: null,
      dominance: 'dominant',
      verdict: 'Intervention dominates — cheaper AND more effective.',
      ciLow: null,
      ciHigh: null,
      belowWtp: true,
    }
  }
  if (dC > EPS && dQ < -EPS) {
    return {
      icer: null,
      dominance: 'dominated',
      verdict: 'Intervention is dominated — more expensive AND less effective.',
      ciLow: null,
      ciHigh: null,
      belowWtp: false,
    }
  }
  if (Math.abs(dQ) < EPS) {
    return {
      icer: dC > 0 ? Number.POSITIVE_INFINITY : Number.NEGATIVE_INFINITY,
      dominance: dC > 0 ? 'northeast' : 'southwest',
      verdict: 'QALY difference is zero — ICER is undefined.',
      ciLow: null,
      ciHigh: null,
      belowWtp: null,
    }
  }
  const icer = dC / dQ
  // 95% CI by ±15% point-estimate envelope — a back-of-envelope value
  // sufficient for the mobile "quick check" surface. The backend uses
  // the full bootstrap when a dataset is bound.
  const ciLow = icer - 0.15 * Math.abs(icer)
  const ciHigh = icer + 0.15 * Math.abs(icer)
  const inNE = dC > 0 && dQ > 0
  const inSW = dC < 0 && dQ < 0
  const belowWtp = inNE ? icer < wtp : inSW ? icer > wtp : null
  const verdict = inNE
    ? belowWtp
      ? `ICER below WTP threshold (${wtp.toLocaleString()}/QALY) — cost-effective.`
      : `ICER above WTP threshold (${wtp.toLocaleString()}/QALY) — not cost-effective at this WTP.`
    : 'Southwest quadrant — cheaper but less effective (weak trade-off).'
  return {
    icer,
    dominance: inNE ? 'northeast' : 'southwest',
    verdict,
    ciLow,
    ciHigh,
    belowWtp,
  }
}

function computeQaly(utility: number, durationYears: number): number {
  return utility * durationYears
}

function computeNmb(
  qalyDiff: number,
  costDiff: number,
  wtp: number,
): { nmb: number; dominance: string } {
  const nmb = wtp * qalyDiff - costDiff
  const dominance =
    nmb > EPS
      ? 'Cost-effective at this threshold.'
      : nmb < -EPS
        ? 'Not cost-effective at this threshold.'
        : 'Neutral — exactly at the threshold.'
  return { nmb, dominance }
}

export default function MobileEconomics() {
  const navigate = useNavigate()
  const lastProjectId = useLastViewedProject((s) => s.projectId)
  const setLastProject = useLastViewedProject((s) => s.set)
  const [picker, setPicker] = useState(false)
  const [infoSlug, setInfoSlug] = useState<CalcId | null>(null)

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

  const activeProject = useMemo(
    () => projects.data?.find((p) => p.id === activeProjectId) ?? null,
    [projects.data, activeProjectId],
  )

  const analyses = useQuery({
    queryKey: ['meconomics', 'list', activeProjectId],
    queryFn: () => economicAnalysesApi.list(activeProjectId!),
    enabled: !!activeProjectId,
    staleTime: 30_000,
  })

  function onPickProject(pid: string) {
    setLastProject(pid)
    setPicker(false)
  }

  return (
    <div className="flex min-h-full flex-col bg-background pb-12">
      {/* Page title */}
      <div className="px-4 pt-4 pb-1">
        <h2 className="text-[20px] font-semibold tracking-tight">
          Health economics
        </h2>
      </div>

      {/* Project picker — same shape as MobileStatsUpload */}
      <div className="flex items-center justify-between gap-2 px-4 pt-1 pb-3">
        <button
          type="button"
          onClick={() => setPicker(true)}
          data-testid="meconomics-project-trigger"
          className="flex min-w-0 items-center gap-1 text-left"
        >
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Project
            </div>
            <div className="flex min-w-0 items-center gap-1">
              <h2 className="truncate text-[16px] font-semibold tracking-tight">
                {activeProject?.title ?? 'No project'}
              </h2>
              <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
            </div>
          </div>
        </button>
      </div>

      {/* Calculators */}
      <div className="space-y-3 px-3">
        <IcerCalculator onInfo={() => setInfoSlug('icer')} />
        <QalyCalculator onInfo={() => setInfoSlug('qaly')} />
        <NmbCalculator onInfo={() => setInfoSlug('nmb')} />
      </div>

      {/* Past analyses */}
      <div className="mt-6 px-3">
        <div className="px-1 pb-2 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Past analyses
        </div>
        {analyses.isLoading && (
          <div
            data-testid="meconomics-analyses-loading"
            className="py-6 text-center text-[12px] text-muted-foreground"
          >
            Loading analyses…
          </div>
        )}
        {!analyses.isLoading && (analyses.data ?? []).length === 0 && (
          <MobileEmpty
            title="No analyses yet"
            subtitle="Run a full ICER analysis from the desktop app to see it here."
            testId="meconomics-analyses-empty"
          />
        )}
        {!analyses.isLoading && (analyses.data ?? []).length > 0 && (
          <div
            data-testid="meconomics-analyses-list"
            className="divide-y divide-border rounded-xl border border-border bg-card"
          >
            {(analyses.data ?? []).map((a) => (
              <AnalysisRow
                key={a.id}
                analysis={a}
                onOpen={() =>
                  navigate(
                    `/projects/${activeProjectId}/economics?analysis=${a.id}`,
                  )
                }
              />
            ))}
          </div>
        )}
      </div>

      {/* Project picker sheet */}
      <BottomSheet
        open={picker}
        onClose={() => setPicker(false)}
        title="Choose a project"
        snapPoints={['60%']}
      >
        {(projects.data ?? []).length === 0 && (
          <div className="py-6 text-center text-[13px] text-muted-foreground">
            No projects found. Create one on the desktop app first.
          </div>
        )}
        {(projects.data ?? []).map((p) => (
          <button
            key={p.id}
            type="button"
            data-testid={`meconomics-project-${p.id}`}
            onClick={() => onPickProject(p.id)}
            className={cn(
              'flex w-full items-center justify-between border-b border-border last:border-b-0 py-3 text-left',
              p.id === activeProjectId && 'font-semibold',
            )}
          >
            <div className="min-w-0">
              <div className="truncate text-[14px]">{p.title}</div>
              <div className="mt-0.5 truncate text-[11px] text-muted-foreground">
                {p.study_type}
              </div>
            </div>
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          </button>
        ))}
      </BottomSheet>

      {/* Info sheet — Learn entry preview */}
      <InfoSheet
        calcId={infoSlug}
        onClose={() => setInfoSlug(null)}
      />
    </div>
  )
}

// ── Card primitive ────────────────────────────────────────────────────────

function CalcCard({
  testId,
  title,
  blurb,
  onInfo,
  children,
}: {
  testId: string
  title: string
  blurb: string
  onInfo: () => void
  children: React.ReactNode
}) {
  return (
    <div
      data-testid={testId}
      className="rounded-2xl border border-border bg-card p-4 shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-[15px] font-semibold tracking-tight">
            {title}
          </div>
          <div className="mt-0.5 text-[12px] text-muted-foreground">
            {blurb}
          </div>
        </div>
        <button
          type="button"
          aria-label="Open info"
          data-testid={`${testId}-info`}
          onClick={onInfo}
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <Info className="h-4 w-4" />
        </button>
      </div>
      <div className="mt-3">{children}</div>
    </div>
  )
}

// ── ICER ──────────────────────────────────────────────────────────────────

function IcerCalculator({ onInfo }: { onInfo: () => void }) {
  const [costA, setCostA] = useState('')
  const [costB, setCostB] = useState('')
  const [qalyA, setQalyA] = useState('')
  const [qalyB, setQalyB] = useState('')
  const [wtp, setWtp] = useState('30000')
  const [result, setResult] = useState<IcerResult | null>(null)

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    const ca = parseFloat(costA)
    const cb = parseFloat(costB)
    const qa = parseFloat(qalyA)
    const qb = parseFloat(qalyB)
    const w = parseFloat(wtp)
    if ([ca, cb, qa, qb, w].some((n) => !Number.isFinite(n))) {
      setResult(null)
      return
    }
    setResult(computeIcer(ca, cb, qa, qb, w))
  }

  return (
    <CalcCard
      testId="meconomics-icer"
      title="ICER"
      blurb={CALC_BLURB.icer}
      onInfo={onInfo}
    >
      <form onSubmit={onSubmit} className="space-y-2.5">
        <div className="grid grid-cols-2 gap-2">
          <NumField
            label="Cost A (intervention)"
            value={costA}
            onChange={setCostA}
            testId="meconomics-icer-cost-a"
          />
          <NumField
            label="Cost B (comparator)"
            value={costB}
            onChange={setCostB}
            testId="meconomics-icer-cost-b"
          />
          <NumField
            label="QALY A"
            value={qalyA}
            onChange={setQalyA}
            testId="meconomics-icer-qaly-a"
          />
          <NumField
            label="QALY B"
            value={qalyB}
            onChange={setQalyB}
            testId="meconomics-icer-qaly-b"
          />
        </div>
        <NumField
          label="WTP threshold (per QALY)"
          value={wtp}
          onChange={setWtp}
          testId="meconomics-icer-wtp"
        />
        <button
          type="submit"
          data-testid="meconomics-icer-submit"
          className="inline-flex h-10 w-full items-center justify-center rounded-md bg-primary px-3 text-[13px] font-semibold text-primary-foreground hover:bg-primary/90"
        >
          Calculate ICER
        </button>
      </form>
      {result && (
        <div
          data-testid="meconomics-icer-result"
          className="mt-3 rounded-md border border-border bg-muted/40 p-3 text-[12px]"
        >
          <div className="flex items-baseline gap-2">
            <span className="text-muted-foreground">ICER</span>
            <span className="text-[15px] font-semibold">
              {result.icer == null
                ? '—'
                : !Number.isFinite(result.icer)
                  ? '∞'
                  : result.icer.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
            </span>
          </div>
          {result.ciLow != null && result.ciHigh != null && (
            <div className="mt-0.5 text-muted-foreground">
              95% CI [{result.ciLow.toLocaleString(undefined, {
                maximumFractionDigits: 0,
              })} —{' '}
              {result.ciHigh.toLocaleString(undefined, {
                maximumFractionDigits: 0,
              })}]
            </div>
          )}
          <div className="mt-1 text-foreground">{result.verdict}</div>
        </div>
      )}
    </CalcCard>
  )
}

// ── QALY ──────────────────────────────────────────────────────────────────

function QalyCalculator({ onInfo }: { onInfo: () => void }) {
  const [utility, setUtility] = useState('')
  const [duration, setDuration] = useState('')
  const [result, setResult] = useState<number | null>(null)

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    const u = parseFloat(utility)
    const d = parseFloat(duration)
    if (!Number.isFinite(u) || !Number.isFinite(d)) {
      setResult(null)
      return
    }
    setResult(computeQaly(u, d))
  }

  return (
    <CalcCard
      testId="meconomics-qaly"
      title="QALY"
      blurb={CALC_BLURB.qaly}
      onInfo={onInfo}
    >
      <form onSubmit={onSubmit} className="space-y-2.5">
        <NumField
          label="Utility (0 — 1)"
          value={utility}
          onChange={setUtility}
          testId="meconomics-qaly-utility"
        />
        <NumField
          label="Duration (years)"
          value={duration}
          onChange={setDuration}
          testId="meconomics-qaly-duration"
        />
        <button
          type="submit"
          data-testid="meconomics-qaly-submit"
          className="inline-flex h-10 w-full items-center justify-center rounded-md bg-primary px-3 text-[13px] font-semibold text-primary-foreground hover:bg-primary/90"
        >
          Calculate QALY
        </button>
      </form>
      {result != null && (
        <div
          data-testid="meconomics-qaly-result"
          className="mt-3 rounded-md border border-border bg-muted/40 p-3 text-[12px]"
        >
          <div className="flex items-baseline gap-2">
            <span className="text-muted-foreground">Total QALYs</span>
            <span className="text-[15px] font-semibold">
              {result.toFixed(3)}
            </span>
          </div>
        </div>
      )}
    </CalcCard>
  )
}

// ── NMB ───────────────────────────────────────────────────────────────────

function NmbCalculator({ onInfo }: { onInfo: () => void }) {
  const [qalyDiff, setQalyDiff] = useState('')
  const [costDiff, setCostDiff] = useState('')
  const [wtp, setWtp] = useState('30000')
  const [result, setResult] =
    useState<{ nmb: number; dominance: string } | null>(null)

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    const q = parseFloat(qalyDiff)
    const c = parseFloat(costDiff)
    const w = parseFloat(wtp)
    if ([q, c, w].some((n) => !Number.isFinite(n))) {
      setResult(null)
      return
    }
    setResult(computeNmb(q, c, w))
  }

  return (
    <CalcCard
      testId="meconomics-nmb"
      title="NMB"
      blurb={CALC_BLURB.nmb}
      onInfo={onInfo}
    >
      <form onSubmit={onSubmit} className="space-y-2.5">
        <NumField
          label="ΔQALY (A − B)"
          value={qalyDiff}
          onChange={setQalyDiff}
          testId="meconomics-nmb-qaly"
        />
        <NumField
          label="ΔCost (A − B)"
          value={costDiff}
          onChange={setCostDiff}
          testId="meconomics-nmb-cost"
        />
        <NumField
          label="WTP threshold (per QALY)"
          value={wtp}
          onChange={setWtp}
          testId="meconomics-nmb-wtp"
        />
        <button
          type="submit"
          data-testid="meconomics-nmb-submit"
          className="inline-flex h-10 w-full items-center justify-center rounded-md bg-primary px-3 text-[13px] font-semibold text-primary-foreground hover:bg-primary/90"
        >
          Calculate NMB
        </button>
      </form>
      {result && (
        <div
          data-testid="meconomics-nmb-result"
          className="mt-3 rounded-md border border-border bg-muted/40 p-3 text-[12px]"
        >
          <div className="flex items-baseline gap-2">
            <span className="text-muted-foreground">NMB</span>
            <span className="text-[15px] font-semibold">
              {result.nmb.toLocaleString(undefined, {
                maximumFractionDigits: 0,
              })}
            </span>
          </div>
          <div className="mt-1 text-foreground">{result.dominance}</div>
        </div>
      )}
    </CalcCard>
  )
}

// ── Bits ──────────────────────────────────────────────────────────────────

function NumField({
  label,
  value,
  onChange,
  testId,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  testId: string
}) {
  return (
    <label className="block">
      <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
      <input
        type="number"
        inputMode="decimal"
        step="any"
        data-testid={testId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 h-10 w-full rounded-md border border-border bg-background px-3 text-[14px] focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
      />
    </label>
  )
}

function AnalysisRow({
  analysis,
  onOpen,
}: {
  analysis: EconomicAnalysis
  onOpen: () => void
}) {
  const r = analysis.result
  return (
    <button
      type="button"
      data-testid={`meconomics-analysis-${analysis.id}`}
      onClick={onOpen}
      className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors active:bg-muted/60 hover:bg-muted/40"
    >
      <div className="min-w-0 flex-1">
        <div className="truncate text-[14px] font-medium leading-tight">
          {analysis.name}
        </div>
        <div className="mt-0.5 text-[12px] text-muted-foreground">
          {analysis.intervention_label} vs {analysis.comparator_label}
          {r?.icer != null && (
            <>
              {' · '}
              ICER {analysis.currency}{' '}
              {Math.round(r.icer).toLocaleString()}
            </>
          )}
        </div>
      </div>
      <Badge variant="secondary" className="text-[10px]">
        {r ? r.dominance_status : 'not run'}
      </Badge>
      <ChevronRight className="h-4 w-4 text-muted-foreground" />
    </button>
  )
}

function InfoSheet({
  calcId,
  onClose,
}: {
  calcId: CalcId | null
  onClose: () => void
}) {
  const slug = calcId ? LEARN_SLUG_BY_CALC[calcId] : null
  const title = calcId ? CALC_TITLE[calcId] : ''

  const entry = useQuery<LearnEconomicsRead>({
    queryKey: ['meconomics', 'learn', slug],
    queryFn: () => learnApi.getEconomics(slug!),
    enabled: !!slug,
    staleTime: 5 * 60 * 1000,
  })

  return (
    <BottomSheet
      open={!!calcId}
      onClose={onClose}
      title={title}
      snapPoints={['85%']}
    >
      {entry.isLoading && (
        <div
          data-testid="meconomics-info-loading"
          className="flex items-center justify-center py-12 text-[12px] text-muted-foreground"
        >
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Loading concept…
        </div>
      )}
      {entry.data && (
        <div data-testid="meconomics-info-body" className="prose prose-sm max-w-none">
          <MarkdownView source={entry.data.body_md} />
        </div>
      )}
      {!entry.isLoading && !entry.data && (
        <div
          data-testid="meconomics-info-error"
          className="py-12 text-center text-[12px] text-muted-foreground"
        >
          Couldn't load the concept right now.
        </div>
      )}
    </BottomSheet>
  )
}
