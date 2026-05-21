/**
 * Phase M4.3 — Page 3 of the mobile Statistics wizard.
 *
 * Route: ``/m/stats/:datasetId/pick-analysis``.
 *
 * Vertical list of cards (one per analysis type in
 * ``MOBILE_ANALYSES``). Each card carries a short title, a 1-line
 * blurb and an "outcome hint" badge so the user picks the test that
 * matches their data shape, not the one with the most familiar name.
 *
 * Tapping a card navigates to step 4
 * (``/m/stats/:datasetId/configure/:analysisType``).
 *
 * A trailing muted card surfaces the desktop escape hatch — anything
 * advanced (mixed-effects, PSM, sensitivity analyses) lives on
 * desktop and is intentionally NOT exposed on mobile.
 */
import { ChevronRight, Monitor } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'

import { MobileHeader } from '../components/MobileHeader'
import { MOBILE_ANALYSES, type MobileAnalysisType } from '../lib/statsWizard'

export default function MobileStatsPickAnalysis() {
  const navigate = useNavigate()
  const { datasetId } = useParams<{ datasetId: string }>()

  function onPick(t: MobileAnalysisType) {
    navigate(`/m/stats/${datasetId}/configure/${t}`)
  }

  return (
    <div className="flex min-h-full flex-col bg-background pb-12">
      <MobileHeader
        title="Choose an analysis"
        onBack={() => navigate(`/m/stats/${datasetId}/preview`)}
      />

      <div className="px-3 pt-3" data-testid="mstats-analysis-list">
        <div className="space-y-2">
          {MOBILE_ANALYSES.map((a) => (
            <button
              key={a.type}
              type="button"
              data-testid={`mstats-analysis-${a.type}`}
              onClick={() => onPick(a.type)}
              className="flex w-full items-start gap-3 rounded-xl border border-border bg-card px-4 py-3 text-left transition-colors active:bg-muted/60 hover:bg-muted/40"
            >
              <div className="min-w-0 flex-1">
                <div className="text-[14px] font-semibold leading-tight">
                  {a.title}
                </div>
                <div className="mt-1 text-[12px] text-muted-foreground">
                  {a.blurb}
                </div>
                <div className="mt-2 inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
                  {a.outcomeHint}
                </div>
              </div>
              <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-muted-foreground" />
            </button>
          ))}
        </div>

        {/* Desktop escape hatch */}
        <div
          data-testid="mstats-desktop-hint"
          className="mt-6 flex items-start gap-3 rounded-xl border border-dashed border-border bg-muted/30 px-4 py-3"
        >
          <Monitor className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
          <div className="min-w-0 flex-1 text-[12px] text-muted-foreground">
            <div className="font-medium text-foreground">
              Need something more advanced?
            </div>
            <div className="mt-0.5">
              Mixed-effects models, propensity-score matching, transformations
              and sensitivity analyses live in the desktop app. Open this
              project on a Mac or PC to access them.
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
