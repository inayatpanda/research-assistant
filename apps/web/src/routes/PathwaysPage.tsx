import {
  Activity,
  ArrowLeft,
  BookOpen,
  ClipboardList,
  GitCompare,
  LineChart,
  Microscope,
  Users,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { AgreementWizard } from '@/components/pathways/AgreementWizard'
import { DiagnosticWizard } from '@/components/pathways/DiagnosticWizard'
import { RiskFactorsWizard } from '@/components/pathways/RiskFactorsWizard'
import { SurvivalWizard } from '@/components/pathways/SurvivalWizard'
import { TwoGroupWizard } from '@/components/pathways/TwoGroupWizard'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useDatasets } from '@/hooks/useDatasets'
import type { PathwayKey } from '@/lib/api'

type PathwayCardSpec = {
  key: PathwayKey
  title: string
  question: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  learnSlug: string
}

const PATHWAYS: PathwayCardSpec[] = [
  {
    key: 'two-group',
    title: 'Two-group comparison',
    question: 'Does outcome X differ between groups A and B?',
    description:
      'Auto-picks Student / Welch / Mann-Whitney for numeric outcomes, or chi-square / Fisher for categorical outcomes.',
    icon: GitCompare,
    learnSlug: 'independent-t-test',
  },
  {
    key: 'risk-factors',
    title: 'Risk factor identification',
    question: 'What predicts outcome Y?',
    description:
      'Univariable + multivariable regression side-by-side, with optional confounder adjustment.',
    icon: ClipboardList,
    learnSlug: 'logistic-regression',
  },
  {
    key: 'survival',
    title: 'Time to event / survival',
    question: 'How long until event Z, and what predicts it?',
    description:
      'Kaplan-Meier, optional log-rank stratification, and Cox proportional hazards with PH check.',
    icon: LineChart,
    learnSlug: 'kaplan-meier',
  },
  {
    key: 'diagnostic',
    title: 'Diagnostic accuracy',
    question: 'How well does test X identify condition Y?',
    description:
      'ROC + AUC for continuous tests, 2x2 sens/spec/PPV/NPV for binary tests, and optional Bayes post-test probability.',
    icon: Microscope,
    learnSlug: 'roc-auc',
  },
  {
    key: 'agreement',
    title: 'Agreement / reliability',
    question: 'Do two raters or methods agree?',
    description:
      'ICC + Bland-Altman for continuous raters, or Cohen / weighted kappa for categorical raters.',
    icon: Users,
    learnSlug: 'cohens-kappa',
  },
]

export default function PathwaysPage() {
  const { projectId = '' } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [pathway, setPathway] = useState<PathwayKey | null>(null)
  const { data: datasets = [], isLoading } = useDatasets(projectId)
  const [datasetId, setDatasetId] = useState<string | null>(null)
  const dataset = datasets.find((d) => d.id === datasetId) ?? datasets[0] ?? null
  const effectiveDatasetId = datasetId ?? dataset?.id ?? null

  if (!pathway) {
    return (
      <div
        className="mx-auto w-full max-w-6xl space-y-6 p-6"
        data-testid="pathways-page"
      >
        <header className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Activity className="h-4 w-4" />
            <span>Research Pathways</span>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Pick a pathway
          </h1>
          <p className="text-sm text-muted-foreground">
            Guided clinical-research workflows. Pick the question, choose your
            columns, and the app picks the right test and writes
            manuscript-ready prose.
          </p>
        </header>
        <ul className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {PATHWAYS.map((p) => (
            <li key={p.key}>
              <button
                type="button"
                className="group h-full w-full rounded-lg border border-border bg-white p-5 text-left transition-shadow hover:shadow-md"
                onClick={() => setPathway(p.key)}
                data-testid={`pathway-card-${p.key}`}
              >
                <div className="flex items-start gap-3">
                  <p.icon className="h-6 w-6 text-primary shrink-0" />
                  <div className="min-w-0">
                    <h2 className="text-sm font-semibold">{p.title}</h2>
                    <p className="text-xs text-muted-foreground italic">
                      {p.question}
                    </p>
                    <p className="mt-2 text-sm text-muted-foreground">
                      {p.description}
                    </p>
                    <Link
                      to={`/projects/${projectId}/learn?slug=${p.learnSlug}`}
                      className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <BookOpen className="h-3 w-3" />
                      Learn more
                    </Link>
                  </div>
                </div>
              </button>
            </li>
          ))}
        </ul>
      </div>
    )
  }

  const spec = PATHWAYS.find((p) => p.key === pathway)!

  return (
    <div
      className="mx-auto w-full max-w-5xl space-y-4 p-6"
      data-testid={`pathway-wizard-${pathway}`}
    >
      <header className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => setPathway(null)}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3 w-3" /> Back to pathways
        </button>
        <button
          type="button"
          onClick={() => navigate(`/projects/${projectId}/statistics`)}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          Open Statistics workbench
        </button>
      </header>
      <div>
        <h1 className="text-lg font-semibold">{spec.title}</h1>
        <p className="text-sm text-muted-foreground italic">{spec.question}</p>
      </div>

      <div className="rounded-lg border border-border bg-white p-4 space-y-3">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading datasets...</p>
        ) : datasets.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No datasets in this project yet. Upload one from the Statistics
            page first.
          </p>
        ) : (
          <div className="max-w-md space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Dataset
            </label>
            <Select
              value={effectiveDatasetId ?? undefined}
              onValueChange={(v) => setDatasetId(v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Pick a dataset" />
              </SelectTrigger>
              <SelectContent>
                {datasets.map((d) => (
                  <SelectItem key={d.id} value={d.id}>
                    {d.filename}{' '}
                    <span className="text-[11px] text-muted-foreground">
                      ({d.n_rows} rows)
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {dataset ? (
          <div className="pt-2">
            {pathway === 'two-group' ? (
              <TwoGroupWizard projectId={projectId} dataset={dataset} />
            ) : null}
            {pathway === 'risk-factors' ? (
              <RiskFactorsWizard projectId={projectId} dataset={dataset} />
            ) : null}
            {pathway === 'survival' ? (
              <SurvivalWizard projectId={projectId} dataset={dataset} />
            ) : null}
            {pathway === 'diagnostic' ? (
              <DiagnosticWizard projectId={projectId} dataset={dataset} />
            ) : null}
            {pathway === 'agreement' ? (
              <AgreementWizard projectId={projectId} dataset={dataset} />
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  )
}
