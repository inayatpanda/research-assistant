/**
 * Phase M4 — Mobile Statistics wizard support types.
 *
 * The wizard exposes a small, opinionated catalogue of analyses (the
 * desktop side has a much wider catalogue plus mixed-effects, PSM and
 * the like). Each analysis type maps onto the existing
 * ``POST /api/projects/{id}/datasets/{ds}/analyses`` endpoint via a
 * ``(question_type, chosen_test, variables)`` triple — exactly the
 * shape the desktop ``NewAnalysisWizard`` uses, so M5 (mini-apps) and
 * future post-hoc work can reuse the same payload.
 *
 * Why a separate file: the wizard is split across five pages, each
 * mounted at a distinct route. Keeping the catalogue + helpers here
 * means we don't import the kitchen-sink desktop wizard module on
 * mobile, and the linear pages share a single source of truth.
 */
import type {
  DatasetVariable,
  QuestionType,
  TestKey,
  VariableType,
} from '@/lib/api'

/**
 * Analysis types exposed on mobile. We use a deliberately small set —
 * the heavyweight tests (mixed-effects, PSM, transformations,
 * sensitivity analyses) stay desktop-only. The keys here are the
 * URL segment (``/m/stats/:datasetId/configure/:analysisType``).
 */
export type MobileAnalysisType =
  | 't_test'
  | 'anova'
  | 'chi_square'
  | 'correlation'
  | 'linear_reg'
  | 'logistic_reg'
  | 'survival'

export type AnalysisCatalogueEntry = {
  type: MobileAnalysisType
  title: string
  blurb: string
  /** Question-type the backend understands. Drives recommend/run paths. */
  questionType: QuestionType
  /** The default chosen_test (used when the user hits "Run" directly). */
  chosenTest: TestKey
  /** Hint shown as a small badge under the card title. */
  outcomeHint: string
}

export const MOBILE_ANALYSES: AnalysisCatalogueEntry[] = [
  {
    type: 't_test',
    title: 'Comparing two groups',
    blurb: 'Test whether a numeric outcome differs between two groups (t-test).',
    questionType: 'group_comparison',
    chosenTest: 'independent_t',
    outcomeHint: 'continuous outcome, 2 groups',
  },
  {
    type: 'anova',
    title: 'Comparing 3+ groups',
    blurb: 'Compare a numeric outcome across three or more groups (one-way ANOVA).',
    questionType: 'group_comparison',
    chosenTest: 'one_way_anova',
    outcomeHint: 'continuous outcome, 3+ groups',
  },
  {
    type: 'chi_square',
    title: 'Two categorical variables',
    blurb: 'Test whether two categorical variables are associated (chi-square / Fisher).',
    questionType: 'group_comparison',
    chosenTest: 'chi_squared',
    outcomeHint: 'categorical outcome + categorical predictor',
  },
  {
    type: 'correlation',
    title: 'Linear relationship',
    blurb: 'Measure the strength of a linear relationship (Pearson or Spearman).',
    questionType: 'association',
    chosenTest: 'pearson',
    outcomeHint: 'two numeric variables',
  },
  {
    type: 'linear_reg',
    title: 'Predict a continuous outcome',
    blurb: 'Linear regression — predict a numeric outcome from one or more predictors.',
    questionType: 'association',
    chosenTest: 'linear_regression',
    outcomeHint: 'continuous outcome',
  },
  {
    type: 'logistic_reg',
    title: 'Predict a binary outcome',
    blurb: 'Logistic regression — model the probability of a binary outcome.',
    questionType: 'association',
    chosenTest: 'logistic',
    outcomeHint: 'binary outcome',
  },
  {
    type: 'survival',
    title: 'Time-to-event',
    blurb: 'Kaplan–Meier survival curves + log-rank test.',
    questionType: 'time_to_event',
    chosenTest: 'kaplan_meier',
    outcomeHint: 'time + event indicator',
  },
]

export function findAnalysis(
  t: string | undefined,
): AnalysisCatalogueEntry | null {
  if (!t) return null
  return MOBILE_ANALYSES.find((a) => a.type === t) ?? null
}

/**
 * Per-analysis configuration captured in step 4. We keep this loose
 * (everything optional) so the linear pages can reuse a single state
 * shape; ``buildPayload`` enforces the per-analysis required-field
 * rules.
 */
export type ConfigureState = {
  outcome?: string
  groups?: string
  x?: string
  y?: string
  predictors?: string[]
  time?: string
  event?: string
  method?: 'pearson' | 'spearman'
}

export function effectiveType(v: DatasetVariable): VariableType {
  return v.user_type ?? v.inferred_type
}

/**
 * Filter the dataset's variables by their effective type. Used by the
 * column-picker bottom sheets so a "pick the outcome" field only shows
 * numeric columns, etc.
 */
export function filterByType(
  variables: DatasetVariable[],
  allowed: VariableType[],
): DatasetVariable[] {
  const set = new Set(allowed)
  return variables.filter((v) => set.has(effectiveType(v)))
}

/**
 * Validate that ``state`` is complete for the given analysis type.
 * Returns null on success, or a user-visible message on failure.
 */
export function validateConfigure(
  type: MobileAnalysisType,
  state: ConfigureState,
): string | null {
  switch (type) {
    case 't_test':
    case 'anova':
      if (!state.outcome) return 'Pick an outcome column'
      if (!state.groups) return 'Pick a group column'
      return null
    case 'chi_square':
      if (!state.outcome) return 'Pick the first categorical column'
      if (!state.groups) return 'Pick the second categorical column'
      return null
    case 'correlation':
      if (!state.x) return 'Pick the first numeric column'
      if (!state.y) return 'Pick the second numeric column'
      return null
    case 'linear_reg':
    case 'logistic_reg':
      if (!state.outcome) return 'Pick an outcome column'
      if (!state.predictors || state.predictors.length === 0)
        return 'Pick at least one predictor'
      return null
    case 'survival':
      if (!state.time) return 'Pick a time column'
      if (!state.event) return 'Pick an event-indicator column'
      return null
  }
}

/**
 * Convert ``ConfigureState`` into the ``{question_type, chosen_test,
 * variables}`` triple the backend expects.
 *
 * The shape mirrors ``buildVariablesPayload`` in the desktop wizard.
 * Linear/logistic regressions use ``association`` with x = outcome,
 * y = first predictor, covariates = remaining predictors. That's the
 * convention the existing analyses runner already understands.
 */
export function buildPayload(
  entry: AnalysisCatalogueEntry,
  state: ConfigureState,
): {
  question_type: QuestionType
  chosen_test: TestKey
  variables: Record<string, string | string[]>
} {
  switch (entry.type) {
    case 't_test':
    case 'anova':
    case 'chi_square':
      return {
        question_type: entry.questionType,
        chosen_test: entry.chosenTest,
        variables: { outcome: state.outcome!, groups: state.groups! },
      }
    case 'correlation':
      return {
        question_type: entry.questionType,
        chosen_test: state.method === 'spearman' ? 'spearman' : 'pearson',
        variables: { x: state.x!, y: state.y! },
      }
    case 'linear_reg':
    case 'logistic_reg': {
      const preds = state.predictors ?? []
      const [first, ...rest] = preds
      const vars: Record<string, string | string[]> = {
        x: state.outcome!,
        y: first!,
      }
      if (rest.length > 0) vars.covariates = rest
      const chosen: TestKey =
        entry.type === 'linear_reg'
          ? preds.length > 1
            ? 'multiple_linear'
            : 'linear_regression'
          : 'logistic'
      return {
        question_type: 'association',
        chosen_test: chosen,
        variables: vars,
      }
    }
    case 'survival':
      return {
        question_type: 'time_to_event',
        chosen_test: 'kaplan_meier',
        variables: { time: state.time!, event: state.event! },
      }
  }
}

/**
 * The variable's display label (free-text override) or the canonical
 * name when none is set. The mobile UI prefers the display label
 * everywhere visible (column-picker rows, chips, the configure form).
 */
export function variableLabel(v: DatasetVariable): string {
  return v.display_label && v.display_label.trim().length > 0
    ? v.display_label
    : v.name
}
