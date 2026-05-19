import { BarChart3, Code2, Plus, Scale, Table2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  type Dataset,
  type DatasetVariable,
  type VariableType,
} from '@/lib/api'
import { useDataset, useUpdateVariableType } from '@/hooks/useDatasets'
import { useAnalysesForDataset } from '@/hooks/useAnalyses'
import { useTransformations } from '@/hooks/useTransformations'

import { DataView } from './DataView'
import { PSMWizard } from './PSMWizard'
import { PlotWorkspace } from './PlotWorkspace'
import { SyntaxView } from './SyntaxView'
import { TransformationStackPanel } from './TransformationStackPanel'

const VARIABLE_TYPES: VariableType[] = [
  'numeric',
  'ordinal',
  'nominal',
  'time',
  'event_indicator',
  'unknown',
]

const TYPE_LABELS: Record<VariableType, string> = {
  numeric: 'Numeric',
  ordinal: 'Ordinal',
  nominal: 'Nominal',
  time: 'Time',
  event_indicator: 'Event indicator',
  unknown: 'Unknown',
}

const TYPE_TONE: Record<VariableType, string> = {
  numeric: 'bg-sky-50 text-sky-700 border-sky-200',
  ordinal: 'bg-violet-50 text-violet-700 border-violet-200',
  nominal: 'bg-amber-50 text-amber-700 border-amber-200',
  time: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  event_indicator: 'bg-rose-50 text-rose-700 border-rose-200',
  unknown: 'bg-muted text-muted-foreground border-border',
}

type Tab = 'variables' | 'data' | 'plots'

export function DatasetDetail({
  projectId,
  datasetId,
  onNewAnalysis,
}: {
  projectId: string
  datasetId: string
  onNewAnalysis: (dataset: Dataset) => void
}) {
  const { data: dataset, isLoading } = useDataset(projectId, datasetId)
  const { data: transformations = [] } = useTransformations(
    projectId,
    datasetId,
  )
  const { data: analyses = [] } = useAnalysesForDataset(projectId, datasetId)
  const [tab, setTab] = useState<Tab>('variables')
  const [showSyntax, setShowSyntax] = useState(false)
  const [psmOpen, setPsmOpen] = useState(false)

  if (isLoading || !dataset) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-9 w-2/3" />
        <Skeleton className="h-[300px] w-full rounded-lg" />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <header className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Dataset
          </div>
          <h2 className="mt-1 text-lg font-semibold tracking-tight truncate">
            {dataset.filename}
          </h2>
          <div className="mt-1 text-[12px] text-muted-foreground">
            {dataset.n_rows} rows × {dataset.n_columns} columns
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setPsmOpen(true)}
            data-testid="open-psm"
          >
            <Scale className="h-4 w-4 mr-1.5" />
            PSM
          </Button>
          <Button
            onClick={() => onNewAnalysis(dataset)}
            className="bg-accent hover:bg-accent-hover text-white"
          >
            <Plus className="h-4 w-4 mr-1.5" />
            New analysis
          </Button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_280px] gap-4">
        <div className="space-y-3">
          <nav className="flex items-center gap-1 border-b border-border" role="tablist">
            <TabButton
              active={tab === 'variables'}
              onClick={() => setTab('variables')}
              label="Variables"
            />
            <TabButton
              active={tab === 'data'}
              onClick={() => setTab('data')}
              label="Data view"
              icon={<Table2 className="h-3.5 w-3.5 mr-1" />}
            />
            <TabButton
              active={tab === 'plots'}
              onClick={() => setTab('plots')}
              label="Plots"
              icon={<BarChart3 className="h-3.5 w-3.5 mr-1" />}
            />
          </nav>
          {tab === 'variables' && (
            <VariablesTable projectId={projectId} dataset={dataset} />
          )}
          {tab === 'data' && (
            <DataView projectId={projectId} dataset={dataset} />
          )}
          {tab === 'plots' && (
            <PlotWorkspace projectId={projectId} dataset={dataset} />
          )}
        </div>
        <aside className="space-y-3">
          <TransformationStackPanel
            projectId={projectId}
            datasetId={datasetId}
          />
          <div>
            <Button
              size="sm"
              variant="outline"
              className="w-full text-[12px]"
              onClick={() => setShowSyntax((s) => !s)}
              data-testid="toggle-syntax"
            >
              <Code2 className="h-3.5 w-3.5 mr-1.5" />
              {showSyntax ? 'Hide syntax' : 'Show syntax'}
            </Button>
          </div>
          {showSyntax && (
            <SyntaxView
              dataset={dataset}
              transformations={transformations}
              analyses={analyses}
            />
          )}
        </aside>
      </div>

      <PSMWizard
        open={psmOpen}
        onOpenChange={setPsmOpen}
        projectId={projectId}
        dataset={dataset}
      />
    </div>
  )
}

function TabButton({
  active,
  onClick,
  label,
  icon,
}: {
  active: boolean
  onClick: () => void
  label: string
  icon?: React.ReactNode
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`inline-flex items-center px-3 py-1.5 text-[12px] font-medium -mb-px border-b-2 transition-colors ${
        active
          ? 'border-accent text-accent'
          : 'border-transparent text-muted-foreground hover:text-foreground'
      }`}
    >
      {icon}
      {label}
    </button>
  )
}

function VariablesTable({
  projectId,
  dataset,
}: {
  projectId: string
  dataset: Dataset
}) {
  const update = useUpdateVariableType(projectId, dataset.id)

  return (
    <div className="rounded-lg border border-border bg-white overflow-hidden">
      <div className="grid grid-cols-12 gap-3 px-4 py-2.5 text-[11px] uppercase tracking-wider text-muted-foreground font-medium border-b border-border bg-muted/30">
        <div className="col-span-4">Column</div>
        <div className="col-span-2">Inferred</div>
        <div className="col-span-3">Override</div>
        <div className="col-span-2">Sample</div>
        <div className="col-span-1 text-right">Missing</div>
      </div>
      <ul className="divide-y divide-border">
        {dataset.variables.map((v) => (
          <VariableRow
            key={v.id}
            variable={v}
            onChange={(userType) => {
              update.mutate(
                { variableId: v.id, userType },
                {
                  onSuccess: () => toast.success(`Updated ${v.name}`),
                  onError: (e: Error) => toast.error(e.message),
                },
              )
            }}
          />
        ))}
      </ul>
    </div>
  )
}

function VariableRow({
  variable,
  onChange,
}: {
  variable: DatasetVariable
  onChange: (userType: VariableType | null) => void
}) {
  const inferred = variable.inferred_type
  const current = variable.user_type ?? inferred

  return (
    <li className="grid grid-cols-12 gap-3 items-center px-4 py-2.5 text-[13px]">
      <div className="col-span-4 font-medium truncate">{variable.name}</div>
      <div className="col-span-2">
        <Badge
          variant="outline"
          className={`text-[11px] font-medium ${TYPE_TONE[inferred]}`}
        >
          {TYPE_LABELS[inferred]}
        </Badge>
      </div>
      <div className="col-span-3">
        <Select
          value={current}
          onValueChange={(v) => {
            const next = v as VariableType
            onChange(next === inferred ? null : next)
          }}
        >
          <SelectTrigger className="h-8 text-[12px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {VARIABLE_TYPES.map((t) => (
              <SelectItem key={t} value={t}>
                {TYPE_LABELS[t]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="col-span-2 truncate text-[12px] text-muted-foreground">
        {variable.sample_values.slice(0, 3).join(', ') || '—'}
      </div>
      <div className="col-span-1 text-right text-[12px] text-muted-foreground tabular-nums">
        {variable.n_missing}
      </div>
    </li>
  )
}
