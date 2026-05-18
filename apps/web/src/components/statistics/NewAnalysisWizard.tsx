import { motion } from 'framer-motion'
import {
  ArrowLeft,
  ArrowRight,
  BarChart3,
  GitCompare,
  Handshake,
  Loader2,
  Scale,
  Timer,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
} from '@/components/ui/sheet'
import {
  type Dataset,
  type QuestionType,
  type RecommendationResponse,
  type TestKey,
} from '@/lib/api'
import { cn } from '@/lib/utils'
import {
  useCreateAnalysis,
  useInterpretAnalysis,
  useRecommendAnalysis,
  useRunAnalysis,
} from '@/hooks/useAnalyses'

import { RecommendationCard } from './RecommendationCard'
import {
  VariablePickerStep,
  type VariableSelection,
  buildVariablesPayload,
  isSelectionComplete,
} from './WizardVariableStep'

type Step = 1 | 2 | 3

const QUESTION_OPTIONS: Array<{
  key: QuestionType
  title: string
  blurb: string
  icon: React.ElementType
}> = [
  {
    key: 'group_comparison',
    title: 'Group comparison',
    blurb: 'Compare an outcome across 2+ groups (t-test, ANOVA, chi-squared).',
    icon: GitCompare,
  },
  {
    key: 'association',
    title: 'Association',
    blurb: 'Correlation or regression between variables.',
    icon: BarChart3,
  },
  {
    key: 'time_to_event',
    title: 'Time to event',
    blurb: 'Survival analysis (Kaplan–Meier, Cox).',
    icon: Timer,
  },
  {
    key: 'agreement',
    title: 'Agreement',
    blurb: 'Inter-rater reliability (ICC, Cohen’s kappa).',
    icon: Handshake,
  },
]

export function NewAnalysisWizard({
  open,
  onOpenChange,
  projectId,
  dataset,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: string
  dataset: Dataset | null
}) {
  const [step, setStep] = useState<Step>(1)
  const [questionType, setQuestionType] = useState<QuestionType | null>(null)
  const [selection, setSelection] = useState<VariableSelection>({})
  const [recommendation, setRecommendation] =
    useState<RecommendationResponse | null>(null)
  const [overrideTest, setOverrideTest] = useState<TestKey | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!open) {
      setStep(1)
      setQuestionType(null)
      setSelection({})
      setRecommendation(null)
      setOverrideTest(null)
      setBusy(false)
    }
  }, [open])

  const recommend = useRecommendAnalysis(projectId, dataset?.id ?? '')
  const create = useCreateAnalysis(projectId, dataset?.id ?? '')
  const run = useRunAnalysis(projectId, dataset?.id ?? '')
  const interpret = useInterpretAnalysis(projectId, dataset?.id ?? '')

  if (!dataset) return null

  async function goToRecommendation() {
    if (!dataset || !questionType) return
    try {
      const variables = buildVariablesPayload(questionType, selection)
      const r = await recommend.mutateAsync({
        question_type: questionType,
        variables,
      })
      setRecommendation(r)
      setOverrideTest(null)
      setStep(3)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to get recommendation'
      toast.error(msg)
    }
  }

  async function createRunInterpret() {
    if (!dataset || !questionType || !recommendation) return
    setBusy(true)
    const chosen = overrideTest ?? recommendation.chosen_test
    try {
      const variables = buildVariablesPayload(questionType, selection)
      const analysis = await create.mutateAsync({
        question_type: questionType,
        chosen_test: chosen,
        variables,
      })
      const ran = await run.mutateAsync(analysis.id)
      try {
        await interpret.mutateAsync(ran.id)
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'Interpretation failed'
        toast.warning(`Analysis ran but AI interpretation failed: ${msg}`)
      }
      toast.success('Analysis created and run')
      onOpenChange(false)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Failed to create analysis'
      toast.error(msg)
    } finally {
      setBusy(false)
    }
  }

  const canAdvanceFromStep2 =
    questionType !== null && isSelectionComplete(questionType, selection)

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-xl p-0 flex flex-col"
      >
        <header className="px-6 pt-6 pb-4 border-b border-border">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            New analysis · {dataset.filename}
          </div>
          <h2 className="mt-1 text-lg font-semibold tracking-tight">
            {step === 1 && 'What are you testing?'}
            {step === 2 && 'Pick your variables'}
            {step === 3 && 'Recommended test'}
          </h2>
          <StepIndicator step={step} />
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-5">
          {step === 1 && (
            <QuestionStep
              selected={questionType}
              onSelect={(q) => {
                setQuestionType(q)
                setSelection({})
              }}
            />
          )}

          {step === 2 && questionType && (
            <VariablePickerStep
              dataset={dataset}
              questionType={questionType}
              selection={selection}
              onChange={setSelection}
            />
          )}

          {step === 3 && recommendation && (
            <RecommendationCard
              recommendation={recommendation}
              overrideTest={overrideTest}
              onOverride={setOverrideTest}
            />
          )}
        </div>

        <footer className="px-6 py-4 border-t border-border flex items-center justify-between gap-2">
          <Button
            variant="ghost"
            onClick={() => {
              if (step === 1) onOpenChange(false)
              else if (step === 2) setStep(1)
              else setStep(2)
            }}
            disabled={busy}
          >
            {step === 1 ? (
              'Cancel'
            ) : (
              <>
                <ArrowLeft className="h-4 w-4 mr-1.5" />
                Back
              </>
            )}
          </Button>

          {step === 1 && (
            <Button
              onClick={() => setStep(2)}
              disabled={!questionType}
              className="bg-accent hover:bg-accent-hover text-white"
            >
              Next
              <ArrowRight className="h-4 w-4 ml-1.5" />
            </Button>
          )}
          {step === 2 && (
            <Button
              onClick={goToRecommendation}
              disabled={!canAdvanceFromStep2 || recommend.isPending}
              className="bg-accent hover:bg-accent-hover text-white"
            >
              {recommend.isPending ? (
                <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
              ) : (
                <Scale className="h-4 w-4 mr-1.5" />
              )}
              Get recommendation
            </Button>
          )}
          {step === 3 && (
            <Button
              onClick={createRunInterpret}
              disabled={busy}
              className="bg-accent hover:bg-accent-hover text-white"
            >
              {busy ? (
                <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
              ) : null}
              Create + Run
            </Button>
          )}
        </footer>
      </SheetContent>
    </Sheet>
  )
}

function StepIndicator({ step }: { step: Step }) {
  return (
    <div className="mt-3 flex items-center gap-1.5">
      {[1, 2, 3].map((s) => (
        <div
          key={s}
          className={cn(
            'h-1 flex-1 rounded-full transition-colors',
            s <= step ? 'bg-accent' : 'bg-border',
          )}
        />
      ))}
    </div>
  )
}

function QuestionStep({
  selected,
  onSelect,
}: {
  selected: QuestionType | null
  onSelect: (q: QuestionType) => void
}) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {QUESTION_OPTIONS.map((opt) => {
        const Icon = opt.icon
        const isSelected = selected === opt.key
        return (
          <motion.button
            key={opt.key}
            whileHover={{ scale: 1.01 }}
            whileTap={{ scale: 0.99 }}
            onClick={() => onSelect(opt.key)}
            className={cn(
              'text-left rounded-lg border p-4 bg-white transition-all',
              isSelected
                ? 'border-accent ring-1 ring-accent/30 shadow-sm'
                : 'border-border hover:border-accent/40',
            )}
          >
            <div className="flex items-center gap-2">
              <Icon
                className={cn(
                  'h-4 w-4',
                  isSelected ? 'text-accent' : 'text-muted-foreground',
                )}
              />
              <div className="text-[14px] font-semibold tracking-tight">
                {opt.title}
              </div>
            </div>
            <div className="mt-1.5 text-[12px] text-muted-foreground leading-relaxed">
              {opt.blurb}
            </div>
          </motion.button>
        )
      })}
    </div>
  )
}
