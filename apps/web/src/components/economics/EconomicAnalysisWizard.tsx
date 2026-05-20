import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  useCreateEconomicAnalysis,
  useInterpretEconomicAnalysis,
  usePushEconomicAnalysis,
  useRunEconomicAnalysis,
  useUpdateEconomicAnalysis,
} from '@/hooks/useEconomicAnalyses'
import { economicAnalysesApi } from '@/lib/api'
import type { CostColumnBinding, EconomicAnalysis } from '@/lib/api'

import { CostColumnBinder } from './CostColumnBinder'
import { EconomicAnalysisSetup } from './EconomicAnalysisSetup'
import { EconomicResultsCard } from './EconomicResultsCard'
import { EconomicSensitivityPanel } from './EconomicSensitivityPanel'

export interface EconomicAnalysisWizardProps {
  projectId: string
  /** Dataset whose columns will be bound (optional — analysis can be created without one). */
  datasetId?: string
  /** All column names from the selected dataset, used by the CostColumnBinder. */
  availableColumns: string[]
  /** Optional existing analysis to edit. */
  initialAnalysis?: EconomicAnalysis | null
  /** Callback to navigate / reload after a successful run. */
  onCompleted?: (analysis: EconomicAnalysis) => void
}

type Step = 'setup' | 'bind' | 'run' | 'results'

/**
 * MP18 — End-to-end wizard: setup → bind cost columns → run → results.
 *
 * The wizard keeps in-memory state for the form and only persists once
 * the user advances to "run". After the first run we keep the analysis
 * id and switch to "results" mode (read-only) — the user can re-bind
 * and re-run via the Sensitivity panel.
 */
export function EconomicAnalysisWizard({
  projectId,
  datasetId,
  availableColumns,
  initialAnalysis = null,
  onCompleted,
}: EconomicAnalysisWizardProps) {
  const [step, setStep] = useState<Step>(initialAnalysis ? 'results' : 'setup')
  const [analysis, setAnalysis] = useState<EconomicAnalysis | null>(
    initialAnalysis,
  )
  const [bindings, setBindings] = useState<CostColumnBinding[]>(
    initialAnalysis?.cost_columns?.map((c) => ({
      col: c.col,
      role: c.role as CostColumnBinding['role'],
    })) ?? [],
  )

  const createMutation = useCreateEconomicAnalysis(projectId)
  const updateMutation = useUpdateEconomicAnalysis(projectId, analysis?.id ?? '')
  const runMutation = useRunEconomicAnalysis(projectId, analysis?.id ?? '')
  const interpretMutation = useInterpretEconomicAnalysis(
    projectId,
    analysis?.id ?? '',
  )
  const pushMutation = usePushEconomicAnalysis(projectId, analysis?.id ?? '')

  const handleCreate = async (body: Parameters<typeof createMutation.mutateAsync>[0]) => {
    try {
      const created = await createMutation.mutateAsync({
        ...body,
        dataset_id: datasetId ?? null,
        cost_columns: bindings,
      })
      setAnalysis(created)
      setStep('bind')
    } catch (e) {
      toast.error('Failed to create analysis')
    }
  }

  const handleSaveBindings = async () => {
    if (!analysis) return
    try {
      const updated = await updateMutation.mutateAsync({ cost_columns: bindings })
      setAnalysis(updated)
      setStep('run')
    } catch (e) {
      toast.error('Failed to save bindings')
    }
  }

  const handleRun = async () => {
    if (!analysis) return
    try {
      const run = await runMutation.mutateAsync()
      setAnalysis(run)
      setStep('results')
      onCompleted?.(run)
    } catch (e) {
      toast.error('Run failed')
    }
  }

  const handleInterpret = async () => {
    if (!analysis) return
    try {
      const next = await interpretMutation.mutateAsync()
      setAnalysis(next)
    } catch (e) {
      toast.error('AI interpretation failed')
    }
  }

  const handlePush = async () => {
    if (!analysis) return
    try {
      await pushMutation.mutateAsync('Results')
      toast.success('Pushed to manuscript')
    } catch (e) {
      toast.error('Push failed')
    }
  }

  const handleCheers = async (fmt: 'docx' | 'pdf') => {
    if (!analysis) return
    try {
      const blob = await economicAnalysesApi.cheersReport(
        projectId,
        analysis.id,
        fmt,
      )
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `cheers-report-${analysis.id}.${fmt}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      toast.error('Could not download CHEERS report')
    }
  }

  return (
    <div data-testid="economic-analysis-wizard" className="space-y-4">
      {step === 'setup' && (
        <Card>
          <CardHeader>
            <CardTitle>1. Setup</CardTitle>
          </CardHeader>
          <CardContent>
            <EconomicAnalysisSetup
              onSubmit={handleCreate}
              submitting={createMutation.isPending}
              submitLabel="Save & continue"
            />
          </CardContent>
        </Card>
      )}
      {step === 'bind' && analysis && (
        <Card>
          <CardHeader>
            <CardTitle>2. Bind cost columns</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <CostColumnBinder
              availableColumns={availableColumns}
              bindings={bindings}
              onChange={setBindings}
            />
            <div className="flex justify-between">
              <Button variant="ghost" onClick={() => setStep('setup')}>
                Back
              </Button>
              <Button
                onClick={handleSaveBindings}
                disabled={updateMutation.isPending || bindings.length === 0}
              >
                Save & continue
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
      {step === 'run' && analysis && (
        <Card>
          <CardHeader>
            <CardTitle>3. Run</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Ready to run {analysis.bootstrap_n} bootstrap replicates with seed{' '}
              {analysis.seed}.
            </p>
            <div className="flex justify-between">
              <Button variant="ghost" onClick={() => setStep('bind')}>
                Back
              </Button>
              <Button onClick={handleRun} disabled={runMutation.isPending}>
                {runMutation.isPending ? 'Running…' : 'Run analysis'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
      {step === 'results' && analysis && (
        <>
          <EconomicResultsCard analysis={analysis} />
          <EconomicSensitivityPanel projectId={projectId} analysis={analysis} />
          <Card>
            <CardHeader>
              <CardTitle>Manuscript actions</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button
                onClick={handleInterpret}
                disabled={interpretMutation.isPending || !analysis.result}
              >
                {interpretMutation.isPending
                  ? 'Interpreting…'
                  : 'AI interpret'}
              </Button>
              <Button
                onClick={handlePush}
                disabled={pushMutation.isPending || !analysis.ai_interpretation}
              >
                Push to manuscript
              </Button>
              <Button variant="outline" onClick={() => handleCheers('docx')}>
                CHEERS DOCX
              </Button>
              <Button variant="outline" onClick={() => handleCheers('pdf')}>
                CHEERS PDF
              </Button>
            </CardContent>
          </Card>
          {analysis.ai_interpretation && (
            <Card>
              <CardHeader>
                <CardTitle>AI interpretation</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{analysis.ai_interpretation}</p>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
