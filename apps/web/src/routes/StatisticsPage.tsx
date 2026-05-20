import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  BarChart3,
  Calculator,
  ChevronDown,
  Combine,
  FileText,
  Loader2,
  Workflow,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { toast } from 'sonner'

import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { AnalysisPlanBuilder } from '@/components/statistics/AnalysisPlanBuilder'
import { AnalysisPlanRunner } from '@/components/statistics/AnalysisPlanRunner'
import { CrossDatasetDialog } from '@/components/statistics/CrossDatasetDialog'
import { DatasetDetail } from '@/components/statistics/DatasetDetail'
import { DatasetList } from '@/components/statistics/DatasetList'
import { DatasetUpload } from '@/components/statistics/DatasetUpload'
import { NewAnalysisWizard } from '@/components/statistics/NewAnalysisWizard'
import { OutputViewer } from '@/components/statistics/OutputViewer'
import { PowerCalculatorDialog } from '@/components/statistics/PowerCalculator'
import { Skeleton } from '@/components/ui/skeleton'
import { type Dataset, projectsApi, statsReportApi } from '@/lib/api'
import { pageEnter } from '@/lib/motion'
import { useProjectId } from '@/lib/projectContext'
import { useAnalysesForDataset } from '@/hooks/useAnalyses'
import { useDataset, useDatasets } from '@/hooks/useDatasets'

export default function StatisticsPage() {
  const projectId = useProjectId()
  return <StatisticsInner projectId={projectId} />
}

function StatisticsInner({ projectId }: { projectId: string }) {
  const [params, setParams] = useSearchParams()
  const datasetParam = params.get('dataset')
  const [wizardOpen, setWizardOpen] = useState(false)
  const [wizardDataset, setWizardDataset] = useState<Dataset | null>(null)
  const [powerOpen, setPowerOpen] = useState(false)
  const [crossOpen, setCrossOpen] = useState(false)
  const [plansOpen, setPlansOpen] = useState(false)
  const [reportPending, setReportPending] = useState(false)

  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
  })

  const { data: datasets = [], isLoading } = useDatasets(projectId)

  useEffect(() => {
    if (!datasets.length) return
    if (!datasetParam || !datasets.find((d) => d.id === datasetParam)) {
      const next = new URLSearchParams(params)
      next.set('dataset', datasets[0].id)
      setParams(next, { replace: true })
    }
  }, [datasets, datasetParam, params, setParams])

  const activeDatasetId = datasetParam ?? datasets[0]?.id ?? null

  function selectDataset(id: string) {
    const next = new URLSearchParams(params)
    next.set('dataset', id)
    setParams(next, { replace: true })
  }

  return (
    <motion.div
      variants={pageEnter}
      initial="initial"
      animate="animate"
      exit="exit"
      className="max-w-7xl mx-auto px-8 py-10 space-y-8"
    >
      <header className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Statistics · {project?.study_type ?? '—'}
          </div>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight truncate">
            {project?.title ?? 'Loading…'}
          </h1>
          <p className="mt-1 text-[13px] text-muted-foreground">
            Upload a masterchart, pick a research question, and let the assistant
            recommend an appropriate test. Push the interpreted result into your
            Results section.
          </p>
        </div>
        <StatisticsToolbar
          datasetsCount={datasets.length}
          reportPending={reportPending}
          onCrossDataset={() => setCrossOpen(true)}
          onPowerCalculator={() => setPowerOpen(true)}
          onAnalysisPlans={() => setPlansOpen(true)}
          onExportReport={async () => {
            if (!activeDatasetId) {
              toast.error('Pick a dataset first.')
              return
            }
            setReportPending(true)
            try {
              const blob = await statsReportApi.export(
                projectId,
                activeDatasetId,
              )
              const url = URL.createObjectURL(blob)
              const a = document.createElement('a')
              a.href = url
              a.download = 'statistical-report.pdf'
              document.body.appendChild(a)
              a.click()
              document.body.removeChild(a)
              URL.revokeObjectURL(url)
              toast.success('Report downloaded')
            } catch (e) {
              const msg = e instanceof Error ? e.message : 'Export failed'
              toast.error(msg)
            } finally {
              setReportPending(false)
            }
          }}
        />
      </header>

      <div
        className="hidden lg:block min-h-[60vh]"
        data-testid="statistics-resizable-shell"
      >
        <ResizablePanelGroup
          direction="horizontal"
          autoSaveId="divider-widths-statistics"
        >
          <ResizablePanel defaultSize={28} minSize={18} maxSize={45}>
            <aside className="pr-4 space-y-4 h-full overflow-y-auto">
              <DatasetUpload projectId={projectId} compact />
              {isLoading ? (
                <div className="space-y-2">
                  {[0, 1].map((i) => (
                    <Skeleton key={i} className="h-[68px] rounded-lg" />
                  ))}
                </div>
              ) : (
                <DatasetList
                  projectId={projectId}
                  activeId={activeDatasetId}
                  onSelect={selectDataset}
                />
              )}
            </aside>
          </ResizablePanel>
          <ResizableHandle withHandle />
          <ResizablePanel defaultSize={72} minSize={55}>
            <section className="pl-4 space-y-6 h-full overflow-y-auto">
              {activeDatasetId ? (
                <ActiveDatasetPanel
                  projectId={projectId}
                  datasetId={activeDatasetId}
                  onNewAnalysis={(d) => {
                    setWizardDataset(d)
                    setWizardOpen(true)
                  }}
                />
              ) : (
                <EmptyHero />
              )}
            </section>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>

      {/* Below-lg fallback: stack vertically (no resizing on small screens) */}
      <div className="lg:hidden space-y-6">
        <aside className="space-y-4">
          <DatasetUpload projectId={projectId} compact />
          {isLoading ? (
            <div className="space-y-2">
              {[0, 1].map((i) => (
                <Skeleton key={i} className="h-[68px] rounded-lg" />
              ))}
            </div>
          ) : (
            <DatasetList
              projectId={projectId}
              activeId={activeDatasetId}
              onSelect={selectDataset}
            />
          )}
        </aside>
        <section className="space-y-6">
          {activeDatasetId ? (
            <ActiveDatasetPanel
              projectId={projectId}
              datasetId={activeDatasetId}
              onNewAnalysis={(d) => {
                setWizardDataset(d)
                setWizardOpen(true)
              }}
            />
          ) : (
            <EmptyHero />
          )}
        </section>
      </div>

      <NewAnalysisWizard
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        projectId={projectId}
        dataset={wizardDataset}
      />

      <PowerCalculatorDialog open={powerOpen} onOpenChange={setPowerOpen} />
      <CrossDatasetDialog
        open={crossOpen}
        onOpenChange={setCrossOpen}
        projectId={projectId}
        datasets={datasets}
      />

      <Dialog open={plansOpen} onOpenChange={setPlansOpen}>
        <DialogContent className="max-w-4xl" data-testid="analysis-plans-dialog">
          <DialogHeader>
            <DialogTitle>Analysis plans</DialogTitle>
          </DialogHeader>
          <div className="space-y-6">
            <AnalysisPlanBuilder projectId={projectId} />
            <AnalysisPlanRunner projectId={projectId} datasets={datasets} />
          </div>
        </DialogContent>
      </Dialog>
    </motion.div>
  )
}

function ActiveDatasetPanel({
  projectId,
  datasetId,
  onNewAnalysis,
}: {
  projectId: string
  datasetId: string
  onNewAnalysis: (dataset: Dataset) => void
}) {
  const { data: dataset } = useDataset(projectId, datasetId)
  const { data: analyses = [] } = useAnalysesForDataset(projectId, datasetId)

  return (
    <div className="space-y-6">
      <DatasetDetail
        projectId={projectId}
        datasetId={datasetId}
        onNewAnalysis={onNewAnalysis}
      />

      {dataset && (
        <OutputViewer
          projectId={projectId}
          dataset={dataset}
          analyses={analyses}
        />
      )}
    </div>
  )
}

function EmptyHero() {
  return (
    <div className="rounded-lg border border-dashed border-border bg-white/40 p-12 text-center">
      <BarChart3 className="h-8 w-8 mx-auto text-muted-foreground" />
      <div className="mt-3 text-[15px] font-semibold tracking-tight">
        Upload your masterchart to begin
      </div>
      <div className="mt-1 text-[13px] text-muted-foreground">
        CSV or XLSX. The assistant will infer variable types and you can override
        them before running tests.
      </div>
    </div>
  )
}

/**
 * DEMO-FIX-B — Page-level toolbar that collapses to a single "Tools" popover
 * when the viewport is narrower than 1100px so the working area on Statistics
 * doesn't get shrunk by four wide buttons. Uses `window.matchMedia` so it
 * tracks viewport changes live.
 */
function StatisticsToolbar({
  datasetsCount,
  reportPending,
  onCrossDataset,
  onPowerCalculator,
  onAnalysisPlans,
  onExportReport,
}: {
  datasetsCount: number
  reportPending: boolean
  onCrossDataset: () => void
  onPowerCalculator: () => void
  onAnalysisPlans: () => void
  onExportReport: () => void
}) {
  const [compact, setCompact] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const mql = window.matchMedia('(max-width: 1099px)')
    const update = () => setCompact(mql.matches)
    update()
    // Older Safari fallback
    if (mql.addEventListener) {
      mql.addEventListener('change', update)
      return () => mql.removeEventListener('change', update)
    }
    mql.addListener(update)
    return () => mql.removeListener(update)
  }, [])

  const crossBtn = (
    <Button
      variant="outline"
      size="sm"
      onClick={onCrossDataset}
      data-testid="open-cross-dataset"
      disabled={datasetsCount < 2}
      className="justify-start w-full sm:w-auto"
    >
      <Combine className="h-4 w-4 mr-1.5" />
      Cross-dataset op
    </Button>
  )
  const powerBtn = (
    <Button
      variant="outline"
      size="sm"
      onClick={onPowerCalculator}
      data-testid="open-power-calculator"
      className="justify-start w-full sm:w-auto"
    >
      <Calculator className="h-4 w-4 mr-1.5" />
      Power calculator
    </Button>
  )
  const plansBtn = (
    <Button
      variant="outline"
      size="sm"
      onClick={onAnalysisPlans}
      data-testid="open-analysis-plans"
      className="justify-start w-full sm:w-auto"
    >
      <Workflow className="h-4 w-4 mr-1.5" />
      Analysis plans
    </Button>
  )
  const reportBtn = (
    <Button
      variant="outline"
      size="sm"
      onClick={onExportReport}
      disabled={reportPending || datasetsCount === 0}
      data-testid="export-stats-report"
      className="justify-start w-full sm:w-auto"
    >
      {reportPending ? (
        <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
      ) : (
        <FileText className="h-4 w-4 mr-1.5" />
      )}
      Export statistical report
    </Button>
  )

  if (compact) {
    return (
      <div
        className="flex items-center gap-2 shrink-0"
        data-testid="statistics-toolbar-compact"
      >
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              size="sm"
              data-testid="open-tools-menu"
            >
              Tools
              <ChevronDown className="h-3.5 w-3.5 ml-1.5" />
            </Button>
          </PopoverTrigger>
          <PopoverContent
            align="end"
            className="w-60 p-2"
            data-testid="tools-popover"
          >
            <div className="flex flex-col gap-1.5">
              {crossBtn}
              {powerBtn}
              {plansBtn}
              {reportBtn}
            </div>
          </PopoverContent>
        </Popover>
      </div>
    )
  }

  return (
    <div
      className="flex items-center gap-2 shrink-0"
      data-testid="statistics-toolbar-full"
    >
      {crossBtn}
      {powerBtn}
      {plansBtn}
      {reportBtn}
    </div>
  )
}
