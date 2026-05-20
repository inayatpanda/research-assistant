import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { EmptyReviewState } from '@/components/review/EmptyReviewState'
import { ExtractionTable } from '@/components/review/ExtractionTable'
import { LivingReviewPanel } from '@/components/review/LivingReviewPanel'
import { PRISMAFlowChart } from '@/components/review/PRISMAFlowChart'
import { PROSPEROForm } from '@/components/review/PROSPEROForm'
import { CrossDatabaseTranslator } from '@/components/review/sr_depth/CrossDatabaseTranslator'
import { MeSHBrowser } from '@/components/review/sr_depth/MeSHBrowser'
import { NarrativeSynthesisPanel } from '@/components/review/sr_depth/NarrativeSynthesisPanel'
import { OutcomeInstrumentsTable } from '@/components/review/sr_depth/OutcomeInstrumentsTable'
import { SearchStrategyBuilder } from '@/components/review/sr_depth/SearchStrategyBuilder'
import { ReviewHeader } from '@/components/review/ReviewHeader'
import { GRADEAssessmentForm } from '@/components/review/grade/GRADEAssessmentForm'
import { SoFTable } from '@/components/review/grade/SoFTable'
import { ForestPlotView } from '@/components/review/meta/ForestPlotView'
import { FunnelPlotView } from '@/components/review/meta/FunnelPlotView'
import { MetaListPanel } from '@/components/review/meta/MetaListPanel'
import { MetaResultCard } from '@/components/review/meta/MetaResultCard'
import { PerStudyInputs } from '@/components/review/meta/PerStudyInputs'
import { RoBAssessmentForm } from '@/components/review/RoBAssessmentForm'
import { RoBSummaryFigure } from '@/components/review/RoBSummaryFigure'
import { RoBToolPicker } from '@/components/review/RoBToolPicker'
import { ScreeningStageTabs, useScreeningStage } from '@/components/review/ScreeningStageTabs'
import { ScreeningTable } from '@/components/review/ScreeningTable'
import { SearchLog } from '@/components/review/SearchLog'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import {
  articlesApi,
  projectsApi,
  type Article,
  type RoBAssessment,
  type RoBTool,
  type RoBToolDef,
  type ScreeningRecord,
} from '@/lib/api'
import { pageEnter } from '@/lib/motion'
import { cn } from '@/lib/utils'
import { useProjectId } from '@/lib/projectContext'
import {
  useRoBAssessments,
  useRoBTools,
  useScreening,
} from '@/hooks/useReviews'
import { useGradeList, usePushGrade } from '@/hooks/useGrade'
import { useMetaDetail } from '@/hooks/useMeta'

type ReviewTab =
  | 'search'
  | 'screening'
  | 'rob'
  | 'extraction'
  | 'meta'
  | 'prisma'
  | 'grade'
  | 'prospero'
  | 'mesh'
  | 'strategy'
  | 'narrative'
  | 'instruments'
  | 'living'

const TABS: { id: ReviewTab; label: string }[] = [
  { id: 'search', label: 'Search log' },
  { id: 'screening', label: 'Screening' },
  { id: 'rob', label: 'Risk of bias' },
  { id: 'extraction', label: 'Data extraction' },
  { id: 'meta', label: 'Meta-analysis' },
  { id: 'prisma', label: 'PRISMA flow' },
  { id: 'grade', label: 'GRADE' },
  { id: 'prospero', label: 'PROSPERO' },
  { id: 'mesh', label: 'MeSH' },
  { id: 'strategy', label: 'Search strategy' },
  { id: 'narrative', label: 'Narrative synthesis' },
  { id: 'instruments', label: 'Outcome instruments' },
  { id: 'living', label: 'Living review' },
]

export default function SystematicReviewPage() {
  const projectId = useProjectId()
  return <ReviewInner projectId={projectId} />
}

function ReviewInner({ projectId }: { projectId: string }) {
  const [params, setParams] = useSearchParams()
  const rawTab = params.get('tab')
  const tab: ReviewTab = TABS.find((t) => t.id === rawTab)?.id ?? 'search'

  const setTab = (t: ReviewTab) => {
    const next = new URLSearchParams(params)
    next.set('tab', t)
    setParams(next, { replace: true })
  }

  const { data: project, isLoading: projLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
  })

  if (projLoading) {
    return <div className="px-8 py-10 text-[13px] text-muted-foreground">Loading…</div>
  }

  if (project && project.study_type !== 'Systematic Review') {
    return <EmptyReviewState studyType={project.study_type} />
  }

  return (
    <motion.div
      variants={pageEnter}
      initial="initial"
      animate="animate"
      exit="exit"
      className="max-w-screen-2xl mx-auto px-8 py-10 space-y-6"
    >
      <header>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
          Systematic Review
        </div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight truncate">
          {project?.title ?? 'Loading…'}
        </h1>
      </header>

      <ReviewHeader projectId={projectId} />

      <div className="border-b border-border">
        <div className="flex gap-1 overflow-x-auto">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                'relative px-3.5 py-3 text-[13px] font-medium transition-colors whitespace-nowrap',
                tab === t.id ? 'text-foreground' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {t.label}
              {tab === t.id && (
                <motion.div
                  layoutId="review-tab"
                  className="absolute left-2 right-2 -bottom-[1px] h-[2px] rounded-full bg-accent"
                />
              )}
            </button>
          ))}
        </div>
      </div>

      <div className="pt-2">
        {tab === 'search' && <SearchLog projectId={projectId} />}
        {tab === 'screening' && <ScreeningTabContent projectId={projectId} />}
        {tab === 'rob' && <RoBTabContent projectId={projectId} />}
        {tab === 'extraction' && <ExtractionTable projectId={projectId} />}
        {tab === 'meta' && <MetaTabContent projectId={projectId} />}
        {tab === 'prisma' && <PRISMAFlowChart projectId={projectId} />}
        {tab === 'grade' && <GradeTabContent projectId={projectId} />}
        {tab === 'prospero' && <PROSPEROForm projectId={projectId} />}
        {tab === 'mesh' && <MeSHBrowser projectId={projectId} />}
        {tab === 'strategy' && (
          <div className="space-y-6">
            <SearchStrategyBuilder projectId={projectId} />
            <CrossDatabaseTranslator projectId={projectId} />
          </div>
        )}
        {tab === 'narrative' && <NarrativeSynthesisPanel projectId={projectId} />}
        {tab === 'instruments' && <OutcomeInstrumentsTable projectId={projectId} />}
        {tab === 'living' && <LivingReviewPanel projectId={projectId} />}
      </div>
    </motion.div>
  )
}

function ScreeningTabContent({ projectId }: { projectId: string }) {
  const [stage, setStage] = useScreeningStage()
  const { data: allRecords = [] } = useScreening(projectId, undefined)

  const counts = useMemo(() => {
    const c: Record<'title_abstract' | 'full_text', number> = {
      title_abstract: 0,
      full_text: 0,
    }
    for (const r of allRecords as ScreeningRecord[]) {
      if (r.stage === 'title_abstract') c.title_abstract += 1
      else if (r.stage === 'full_text') c.full_text += 1
    }
    return c
  }, [allRecords])

  return (
    <div className="space-y-4">
      <ScreeningStageTabs active={stage} onChange={setStage} counts={counts} />
      <ScreeningTable projectId={projectId} stage={stage} />
    </div>
  )
}

function RoBTabContent({ projectId }: { projectId: string }) {
  const { data: screening = [] } = useScreening(projectId, 'full_text')
  const { data: articles = [] } = useQuery({
    queryKey: ['articles', projectId, { sort: 'created_desc' }],
    queryFn: () => articlesApi.list(projectId, { sort: 'created_desc' }),
  })
  const { data: toolDefs = [] } = useRoBTools(projectId)
  const { data: assessments = [] } = useRoBAssessments(projectId)

  const includedArticles = useMemo(() => {
    const include = new Set(
      (screening as ScreeningRecord[])
        .filter((s) => s.decision === 'include')
        .map((s) => s.article_id),
    )
    return articles.filter((a) => include.has(a.id))
  }, [articles, screening])

  const assessmentByArticle = useMemo(() => {
    const m = new Map<string, (typeof assessments)[number]>()
    for (const a of assessments) m.set(a.article_id, a)
    return m
  }, [assessments])

  const [showSummary, setShowSummary] = useState(false)

  if (toolDefs.length === 0) {
    return <div className="text-[13px] text-muted-foreground">Loading tools…</div>
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-[15px] font-semibold tracking-tight">Risk of bias</h3>
          <div className="text-[12px] text-muted-foreground">
            Assess each included study using the appropriate tool.
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={showSummary ? 'default' : 'outline'}
            size="sm"
            onClick={() => setShowSummary((s) => !s)}
            className={showSummary ? 'bg-accent hover:bg-accent-hover text-white' : ''}
          >
            {showSummary ? 'Hide summary figure' : 'Show summary figure'}
          </Button>
        </div>
      </div>

      {showSummary && (
        <RoBSummaryFigure
          projectId={projectId}
          toolDefs={toolDefs}
          assessments={assessments}
          articles={articles}
        />
      )}

      {includedArticles.length === 0 ? (
        <div className="rounded-md border border-dashed border-border p-6 text-center text-[13px] text-muted-foreground">
          No included studies yet. Mark articles as <span className="font-medium">include</span> at the full-text stage.
        </div>
      ) : (
        <ul className="space-y-2">
          {includedArticles.map((a) => (
            <RoBStudyRow
              key={a.id}
              projectId={projectId}
              article={a}
              toolDefs={toolDefs}
              existing={assessmentByArticle.get(a.id)}
            />
          ))}
        </ul>
      )}
    </div>
  )
}

function MetaTabContent({ projectId }: { projectId: string }) {
  const [params] = useSearchParams()
  const metaId = params.get('meta') || undefined
  const { data: meta, isLoading } = useMetaDetail(projectId, metaId)

  return (
    <div className="flex gap-6">
      <MetaListPanel projectId={projectId} />
      <div className="flex-1 min-w-0 space-y-4">
        {!metaId ? (
          <div className="rounded-md border border-dashed border-border bg-white p-8 text-center text-[13px] text-muted-foreground">
            Select a meta-analysis from the left, or create a new one.
          </div>
        ) : isLoading || !meta ? (
          <div className="text-[12px] text-muted-foreground">Loading…</div>
        ) : (
          <>
            <PerStudyInputs projectId={projectId} meta={meta} />
            <MetaResultCard projectId={projectId} meta={meta} />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-2">
                  Forest plot
                </div>
                <ForestPlotView projectId={projectId} meta={meta} />
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-2">
                  Funnel plot
                </div>
                <FunnelPlotView projectId={projectId} meta={meta} />
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function RoBStudyRow({
  projectId,
  article,
  toolDefs,
  existing,
}: {
  projectId: string
  article: Article
  toolDefs: RoBToolDef[]
  existing: RoBAssessment | undefined
}) {
  const [tool, setTool] = useState<RoBTool | null>(
    (existing?.tool as RoBTool | undefined) ?? null,
  )
  const [open, setOpen] = useState(false)

  const toolDef = toolDefs.find((t) => t.key === tool)
  const overall = existing?.overall_override ?? existing?.overall_auto ?? null

  return (
    <li className="rounded-md border border-border bg-white px-4 py-3 flex items-center gap-4">
      <div className="min-w-0 flex-1">
        <div className="text-[13px] font-medium truncate">{article.title}</div>
        <div className="text-[11px] text-muted-foreground">
          {article.study_design ?? 'design unspecified'}
          {overall && (
            <span className="ml-2 rounded-md border border-border bg-muted/30 px-1.5 py-0.5 text-[10px] uppercase tracking-wider">
              Overall: {overall}
            </span>
          )}
        </div>
      </div>
      <RoBToolPicker
        value={tool}
        onChange={setTool}
        studyDesign={article.study_design}
        tools={toolDefs}
      />
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <Button variant="outline" size="sm" disabled={!tool}>
            {existing ? 'Edit' : 'Assess'}
          </Button>
        </SheetTrigger>
        <SheetContent
          side="right"
          className="w-[520px] sm:max-w-[520px] overflow-y-auto"
        >
          {tool && toolDef && (
            <div className="pt-6 space-y-4">
              <div>
                <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                  {toolDef.label}
                </div>
                <div className="mt-0.5 text-[15px] font-semibold tracking-tight">
                  {article.title}
                </div>
              </div>
              <RoBAssessmentForm
                projectId={projectId}
                articleId={article.id}
                tool={tool}
                toolDef={toolDef}
                existing={
                  existing && existing.tool === tool ? existing : undefined
                }
                onSaved={() => setOpen(false)}
              />
            </div>
          )}
        </SheetContent>
      </Sheet>
    </li>
  )
}

function GradeTabContent({ projectId }: { projectId: string }) {
  const { data: rows = [] } = useGradeList(projectId)
  const push = usePushGrade(projectId)

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-[15px] font-semibold tracking-tight">
            GRADE certainty of evidence
          </h3>
          <div className="text-[12px] text-muted-foreground">
            One row per outcome. Add a new outcome below; the Summary of
            Findings table updates live.
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => push.mutate()}
          disabled={rows.length === 0 || push.isPending}
        >
          {push.isPending ? 'Pushing…' : 'Push SoF to Results'}
        </Button>
      </div>

      <GRADEAssessmentForm projectId={projectId} />

      <div>
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-2">
          Summary of Findings
        </div>
        <SoFTable projectId={projectId} rows={rows} />
      </div>
    </div>
  )
}
