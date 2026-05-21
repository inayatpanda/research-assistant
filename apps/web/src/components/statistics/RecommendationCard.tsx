import { AlertTriangle, Settings2, Sparkles } from 'lucide-react'

import { LearnTooltip } from '@/components/learn/LearnTooltip'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  TEST_LABELS,
  type RecommendationResponse,
  type TestKey,
} from '@/lib/api'

const TEST_KEYS = Object.keys(TEST_LABELS) as TestKey[]

const TEST_LEARN_CONCEPT: Partial<Record<TestKey, string>> = {
  independent_t: 'independent-t-test',
  paired_t: 'paired-t-test',
  mann_whitney: 'mann-whitney-u',
  wilcoxon_signed: 'wilcoxon-signed-rank',
  chi_squared: 'chi-square-independence',
  fisher_exact: 'fisher-exact',
  one_way_anova: 'one-way-anova',
  kruskal_wallis: 'kruskal-wallis',
  rm_anova: 'repeated-measures-anova',
  pearson: 'pearson-correlation',
  spearman: 'spearman-correlation',
  linear_regression: 'linear-regression',
  multiple_linear: 'multiple-linear-regression',
  logistic: 'logistic-regression',
  kaplan_meier: 'kaplan-meier-log-rank',
  cox_ph: 'cox-proportional-hazards',
  icc: 'icc',
  mixed_effects_lm: 'mixed-effects-lm',
}

export function RecommendationCard({
  recommendation,
  overrideTest,
  onOverride,
}: {
  recommendation: RecommendationResponse
  overrideTest: TestKey | null
  onOverride: (test: TestKey | null) => void
}) {
  const effective = overrideTest ?? recommendation.chosen_test
  const isOverridden = overrideTest !== null && overrideTest !== recommendation.chosen_test

  return (
    <div className="rounded-lg border border-border bg-white p-5 space-y-4">
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-accent/10 text-accent shrink-0">
          <Sparkles className="h-4 w-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
            Recommended test
          </div>
          <div className="mt-0.5 text-[15px] font-semibold tracking-tight flex items-center gap-1.5 flex-wrap">
            <LearnTooltip
              concept={
                TEST_LEARN_CONCEPT[effective] ?? effective.replace(/_/g, '-')
              }
              iconOnly
              description={`Open Learn entry for ${TEST_LABELS[effective]}`}
            >
              {TEST_LABELS[effective]}
            </LearnTooltip>
            {isOverridden && (
              <span className="text-[11px] font-medium text-amber-600">
                (overridden from {TEST_LABELS[recommendation.chosen_test]})
              </span>
            )}
          </div>
          <p className="mt-2 text-[13px] text-muted-foreground leading-relaxed">
            {recommendation.rationale}
          </p>
        </div>
      </div>

      {recommendation.assumption_warnings.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-[12px] text-amber-800">
          <div className="flex items-center gap-1.5 font-medium">
            <AlertTriangle className="h-3.5 w-3.5" />
            Assumption warnings
          </div>
          <ul className="mt-1 list-disc pl-5 space-y-0.5">
            {recommendation.assumption_warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <details className="group">
        <summary className="flex items-center gap-1.5 text-[12px] text-muted-foreground hover:text-foreground cursor-pointer">
          <Settings2 className="h-3.5 w-3.5" />
          Use a different test
        </summary>
        <div className="mt-2 flex items-center gap-2">
          <Select
            value={effective}
            onValueChange={(v) => {
              const next = v as TestKey
              onOverride(next === recommendation.chosen_test ? null : next)
            }}
          >
            <SelectTrigger className="h-9 text-[13px] max-w-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TEST_KEYS.map((k) => (
                <SelectItem key={k} value={k}>
                  {TEST_LABELS[k]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {isOverridden && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => onOverride(null)}
              className="text-[12px] h-8"
            >
              Reset
            </Button>
          )}
        </div>
      </details>
    </div>
  )
}
