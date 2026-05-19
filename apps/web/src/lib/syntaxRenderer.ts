/**
 * Phase 13 (MP13) — Syntax view renderer.
 *
 * Emits an R-flavoured pseudo-code trace for a dataset's transformation stack
 * (and optional analyses). Pure functions only — safe to unit-test without a DOM.
 */
import type {
  Analysis,
  Dataset,
  TransformationRead,
  TestKey,
} from './api'

/** Quote a string for R-ish output. Always uses double quotes; escapes inner ". */
function quote(s: string): string {
  return `"${String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`
}

/** Render a JS value as an R-ish literal (string, number, bool, list, NA). */
function literal(v: unknown): string {
  if (v === null || v === undefined) return 'NA'
  if (typeof v === 'string') return quote(v)
  if (typeof v === 'number' || typeof v === 'boolean') return String(v)
  if (Array.isArray(v)) return `c(${v.map(literal).join(', ')})`
  if (typeof v === 'object') {
    return `list(${Object.entries(v as Record<string, unknown>)
      .map(([k, val]) => `${k} = ${literal(val)}`)
      .join(', ')})`
  }
  return String(v)
}

function renderOp(op: TransformationRead): string {
  const args = op.op_args ?? {}
  switch (op.op_type) {
    case 'filter': {
      const expr = typeof args.expr === 'string' ? args.expr : ''
      return `data <- filter(data, ${expr || '...'})`
    }
    case 'mutate': {
      const col = typeof args.column === 'string' ? args.column : 'new_col'
      const expr = typeof args.expr === 'string' ? args.expr : '...'
      return `data <- mutate(data, ${col} = ${expr})`
    }
    case 'select': {
      const cols = Array.isArray(args.columns) ? (args.columns as unknown[]) : []
      return `data <- select(data, ${cols.map(literal).join(', ')})`
    }
    case 'recode': {
      const col = typeof args.column === 'string' ? args.column : 'col'
      const mapping = args.mapping ?? {}
      return `data <- recode(data, ${col}, ${literal(mapping)})`
    }
    case 'drop_na': {
      const cols = Array.isArray(args.columns) ? (args.columns as unknown[]) : []
      return cols.length > 0
        ? `data <- drop_na(data, ${cols.map(literal).join(', ')})`
        : `data <- drop_na(data)`
    }
    case 'log_transform': {
      const col = typeof args.column === 'string' ? args.column : 'col'
      const newCol =
        typeof args.new_column === 'string' && args.new_column
          ? args.new_column
          : `log_${col}`
      return `data <- mutate(data, ${newCol} = log(${col}))`
    }
    case 'z_score': {
      const col = typeof args.column === 'string' ? args.column : 'col'
      const newCol =
        typeof args.new_column === 'string' && args.new_column
          ? args.new_column
          : `z_${col}`
      return `data <- mutate(data, ${newCol} = scale(${col}))`
    }
    case 'group_summarise': {
      const groups = Array.isArray(args.group_by)
        ? (args.group_by as unknown[])
        : []
      const summaries = args.summarise ?? args.summaries ?? {}
      return `data <- group_summarise(data, by = ${literal(groups)}, ${literal(summaries)})`
    }
    default: {
      // Type assertion safety: TransformationOpType is a closed union.
      const opType: string = op.op_type
      return `data <- ${opType}(data, ${literal(args)})`
    }
  }
}

const TEST_FN: Partial<Record<TestKey, string>> = {
  independent_t: 'ttest',
  paired_t: 'ttest_paired',
  mann_whitney: 'wilcox',
  wilcoxon_signed: 'wilcox_signed',
  chi_squared: 'chisq.test',
  fisher_exact: 'fisher.test',
  one_way_anova: 'aov',
  kruskal_wallis: 'kruskal.test',
  rm_anova: 'rm_aov',
  pearson: 'cor.test',
  spearman: 'cor.test',
  linear_regression: 'lm',
  multiple_linear: 'lm',
  logistic: 'glm',
  kaplan_meier: 'survfit',
  cox_ph: 'coxph',
  icc: 'icc',
  cohen_kappa: 'kappa',
  mixed_effects_lm: 'lmer',
  glm_poisson: 'glm',
  glm_binomial: 'glm',
  glm_gamma: 'glm',
  gee: 'gee',
  bootstrap_mean_diff: 'bootstrap',
  permutation_test: 'permutation_test',
  tost_equivalence: 'tost',
  tost_noninferiority: 'tost_noninf',
}

function renderAnalysis(analysis: Analysis, index: number): string {
  const fn = TEST_FN[analysis.chosen_test] ?? analysis.chosen_test
  const variables = analysis.variables ?? {}
  const outcome =
    typeof variables.outcome === 'string' ? variables.outcome : null
  const groups =
    typeof variables.groups === 'string' ? variables.groups : null
  const predictors = Array.isArray(variables.predictors)
    ? (variables.predictors as string[])
    : null
  const resultVar = index === 0 ? 'result' : `result_${index + 1}`

  if (outcome && (groups || predictors)) {
    const rhs = groups ? groups : (predictors ?? []).join(' + ')
    return `${resultVar} <- ${fn}(data, formula = ${outcome} ~ ${rhs})`
  }
  return `${resultVar} <- ${fn}(data, ${literal(variables)})`
}

/**
 * Build an R-flavoured pseudo-code trace for a dataset and its transformation
 * stack. Optional `analyses` are appended in order at the end.
 *
 * The output is deterministic (transformations sorted by `position` ascending)
 * which makes it safe to feed into snapshot-style tests.
 */
export function renderSyntax(
  dataset: Pick<Dataset, 'filename'> | null | undefined,
  transformations: TransformationRead[] | null | undefined,
  analyses?: Analysis[] | null,
): string {
  const lines: string[] = []
  const fname = dataset?.filename ?? 'dataset.csv'
  lines.push(`data <- import(${quote(fname)})`)

  const sorted = (transformations ?? [])
    .slice()
    .sort((a, b) => a.position - b.position)
  for (const op of sorted) {
    lines.push(renderOp(op))
  }
  ;(analyses ?? []).forEach((a, idx) => {
    lines.push(renderAnalysis(a, idx))
  })
  return lines.join('\n')
}
