import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { ProjectSelectGate } from '@/components/library/ProjectSelectGate'
import { EmptyReviewState } from '@/components/review/EmptyReviewState'
import { ExtractionTable } from '@/components/review/ExtractionTable'
import { PRISMAFlowChart } from '@/components/review/PRISMAFlowChart'
import { ReviewHeader } from '@/components/review/ReviewHeader'
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
import { useActiveProject } from '@/lib/projectContext'
import {
  useRoBAssessments,
  useRoBTools,
  useScreening,
} from '@/hooks/useReviews'

type ReviewTab = 'search' | 'screening' | 'rob' | 'extraction' | 'prisma'

const TABS: { id: ReviewTab; label: string }[] = [
  { id: 'search', label: 'Search log' },
  { id: 'screening', label: 'Screening' },
  { id: 'rob', label: 'Risk of bias' },
  { id: 'extraction', label: 'Data extraction' },
  { id: 'prisma', label: 'PRISMA flow' },
]

export default function SystematicReviewPage() {
  const projectId = useActiveProject((s) => s.projectId)
  if (!projectId) return <ProjectSelectGate />
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
      className="max-w-7xl mx-auto px-8 py-10 space-y-6"
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
        {tab === 'prisma' && <PRISMAFlowChart projectId={projectId} />}
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
