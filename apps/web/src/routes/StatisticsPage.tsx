import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { BarChart3 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { ProjectSelectGate } from '@/components/library/ProjectSelectGate'
import { AnalysisResultCard } from '@/components/statistics/AnalysisResultCard'
import { DatasetDetail } from '@/components/statistics/DatasetDetail'
import { DatasetList } from '@/components/statistics/DatasetList'
import { DatasetUpload } from '@/components/statistics/DatasetUpload'
import { NewAnalysisWizard } from '@/components/statistics/NewAnalysisWizard'
import { Skeleton } from '@/components/ui/skeleton'
import { type Dataset, projectsApi } from '@/lib/api'
import { pageEnter } from '@/lib/motion'
import { useActiveProject } from '@/lib/projectContext'
import { useAnalysesForDataset } from '@/hooks/useAnalyses'
import { useDataset, useDatasets } from '@/hooks/useDatasets'

export default function StatisticsPage() {
  const projectId = useActiveProject((s) => s.projectId)
  if (!projectId) return <ProjectSelectGate />
  return <StatisticsInner projectId={projectId} />
}

function StatisticsInner({ projectId }: { projectId: string }) {
  const [params, setParams] = useSearchParams()
  const datasetParam = params.get('dataset')
  const [wizardOpen, setWizardOpen] = useState(false)
  const [wizardDataset, setWizardDataset] = useState<Dataset | null>(null)

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
      <header>
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
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <aside className="lg:col-span-4 space-y-4">
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

        <section className="lg:col-span-8 space-y-6">
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

      {dataset && analyses.length > 0 && (
        <section className="space-y-3">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Analyses ({analyses.length})
          </div>
          <div className="space-y-3">
            {analyses.map((a) => (
              <AnalysisResultCard
                key={a.id}
                projectId={projectId}
                dataset={dataset}
                analysis={a}
              />
            ))}
          </div>
        </section>
      )}

      {dataset && analyses.length === 0 && (
        <div className="rounded-lg border border-dashed border-border bg-white/40 p-8 text-center">
          <BarChart3 className="h-6 w-6 mx-auto text-muted-foreground" />
          <div className="mt-2 text-[14px] font-medium">No analyses yet</div>
          <div className="mt-1 text-[12px] text-muted-foreground">
            Click <span className="font-medium">New analysis</span> to recommend
            and run a statistical test on this dataset.
          </div>
        </div>
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
