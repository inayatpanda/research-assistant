import { useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from '@/components/ui/resizable'
import { EconomicAnalysisWizard } from '@/components/economics/EconomicAnalysisWizard'
import {
  useDeleteEconomicAnalysis,
  useEconomicAnalyses,
} from '@/hooks/useEconomicAnalyses'
import { useDatasets } from '@/hooks/useDatasets'
import { useProjectId } from '@/lib/projectContext'
import type { EconomicAnalysis } from '@/lib/api'

/**
 * MP18 — Health Economics workspace.
 *
 * Layout:
 *   - left column: existing analyses + dataset picker + "new analysis" button
 *   - right column: <EconomicAnalysisWizard> for the active analysis (or
 *     a fresh one)
 */
export default function EconomicsPage() {
  const projectId = useProjectId()
  return <EconomicsInner projectId={projectId} />
}

function EconomicsInner({ projectId }: { projectId: string }) {
  const [activeId, setActiveId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const { data: analyses = [], isLoading } = useEconomicAnalyses(projectId)
  const { data: datasets = [] } = useDatasets(projectId)
  const deleteMutation = useDeleteEconomicAnalysis(projectId)

  const active: EconomicAnalysis | null =
    analyses.find((a) => a.id === activeId) ?? null

  const datasetForAnalysis = active?.dataset_id
    ? datasets.find((d) => d.id === active.dataset_id) ?? null
    : datasets[0] ?? null
  const availableColumns: string[] = datasetForAnalysis
    ? (datasetForAnalysis.variables ?? []).map((v) => v.name)
    : []

  return (
    <div
      className="p-6 h-[calc(100vh-4rem)]"
      data-testid="economics-resizable-shell"
    >
      <ResizablePanelGroup
        direction="horizontal"
        autoSaveId="divider-widths-economics"
      >
        <ResizablePanel defaultSize={25} minSize={18} maxSize={45}>
          <Card className="h-full overflow-y-auto mr-3">
            <CardHeader className="flex flex-row items-center justify-between gap-2">
              <CardTitle className="text-base">Economic analyses</CardTitle>
              <Button
                size="sm"
                variant="default"
                onClick={() => {
                  setActiveId(null)
                  setCreating(true)
                }}
                aria-label="New economic analysis"
              >
                <Plus className="h-4 w-4 mr-1" />
                New
              </Button>
            </CardHeader>
            <CardContent className="space-y-1">
              {isLoading && (
                <div className="text-sm text-muted-foreground">Loading…</div>
              )}
              {!isLoading && analyses.length === 0 && (
                <div className="text-sm text-muted-foreground italic">
                  No analyses yet — create one.
                </div>
              )}
              {analyses.map((a) => (
                <div
                  key={a.id}
                  className={`group flex items-center justify-between rounded-md px-2 py-1 text-sm cursor-pointer hover:bg-muted ${
                    a.id === activeId ? 'bg-muted' : ''
                  }`}
                  onClick={() => {
                    setActiveId(a.id)
                    setCreating(false)
                  }}
                  data-testid={`economic-analysis-card-${a.id}`}
                >
                  <span className="truncate">{a.name}</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="opacity-0 group-hover:opacity-100"
                    onClick={(e) => {
                      e.stopPropagation()
                      if (confirm('Delete this analysis?')) {
                        deleteMutation.mutate(a.id)
                        if (a.id === activeId) setActiveId(null)
                      }
                    }}
                    aria-label={`Delete ${a.name}`}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>
        </ResizablePanel>
        <ResizableHandle withHandle />
        <ResizablePanel defaultSize={75} minSize={55}>
          <div className="pl-3 h-full overflow-y-auto">
            {creating || !active ? (
              <EconomicAnalysisWizard
                projectId={projectId}
                datasetId={datasetForAnalysis?.id}
                availableColumns={availableColumns}
                initialAnalysis={null}
                onCompleted={(a) => {
                  setActiveId(a.id)
                  setCreating(false)
                }}
              />
            ) : (
              <EconomicAnalysisWizard
                projectId={projectId}
                datasetId={active.dataset_id ?? undefined}
                availableColumns={availableColumns}
                initialAnalysis={active}
              />
            )}
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  )
}
