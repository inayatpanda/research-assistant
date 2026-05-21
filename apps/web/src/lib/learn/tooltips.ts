/**
 * Phase 5a — Learn-hub tooltip infrastructure.
 *
 * Provides:
 *   - `getLearnLink(concept)` — map a concept slug to its Learn URL.
 *   - `LEARN_CONCEPT_INDEX`  — explicit concept → stat-test-slug aliases so
 *     surfaces (Statistics page, AI interpretation, etc.) can use familiar
 *     names ("t-test", "anova") that resolve to the canonical slug used
 *     under the hood.
 *
 * Wiring this map across the app is Phase 5c work — this module just
 * publishes the contracts so future PRs can drop in `<LearnTooltip
 * concept="anova" />` without bikeshedding URL formats.
 */

/**
 * The Learn hub is mounted under `/projects/:projectId/learn`, but the
 * generated URLs are project-agnostic so they survive being copy-pasted
 * between projects. The active-project router rewrites them as needed.
 */
const LEARN_BASE_PATH = '/learn'

/**
 * Stable alias table: maps a friendly concept name (case-insensitive) to
 * the canonical stat-test slug shipped in
 * apps/api/src/research_api/learn/stat_tests/*.md. Keep the keys
 * lowercase. When the concept is already a slug, no entry is needed —
 * `getLearnLink` falls back to passing the input through.
 */
export const LEARN_CONCEPT_INDEX: Readonly<Record<string, string>> = Object.freeze({
  't-test': 'independent-t-test',
  'independent-t-test': 'independent-t-test',
  'paired-t-test': 'paired-t-test',
  'one-sample-t-test': 'one-sample-t-test',
  'welch-t-test': 'welch-t-test',
  anova: 'one-way-anova',
  'one-way-anova': 'one-way-anova',
  'two-way-anova': 'two-way-anova',
  'repeated-measures-anova': 'repeated-measures-anova',
  ancova: 'ancova',
  'mann-whitney': 'mann-whitney-u',
  'mann-whitney-u': 'mann-whitney-u',
  wilcoxon: 'wilcoxon-signed-rank',
  'wilcoxon-signed-rank': 'wilcoxon-signed-rank',
  'kruskal-wallis': 'kruskal-wallis',
  friedman: 'friedman',
  'chi-square': 'chi-square-independence',
  'chi-square-independence': 'chi-square-independence',
  'chi-square-goodness-of-fit': 'chi-square-goodness-of-fit',
  'fisher-exact': 'fisher-exact',
  mcnemar: 'mcnemar',
  pearson: 'pearson-correlation',
  'pearson-correlation': 'pearson-correlation',
  spearman: 'spearman-correlation',
  'spearman-correlation': 'spearman-correlation',
  'linear-regression': 'linear-regression',
  'multiple-linear-regression': 'multiple-linear-regression',
  'logistic-regression': 'logistic-regression',
  cox: 'cox-proportional-hazards',
  'cox-proportional-hazards': 'cox-proportional-hazards',
  'kaplan-meier': 'kaplan-meier-log-rank',
  'kaplan-meier-log-rank': 'kaplan-meier-log-rank',
  'shapiro-wilk': 'shapiro-wilk',
  levene: 'levenes-test',
  'levenes-test': 'levenes-test',
  'bland-altman': 'bland-altman',
  icc: 'icc',
  // --- Phase 5b: reporting checklists ---
  consort: 'consort',
  strobe: 'strobe',
  prisma: 'prisma',
  care: 'care',
  squire: 'squire',
  coreq: 'coreq',
  srqr: 'srqr',
  tripod: 'tripod',
  cheers: 'cheers',
  stard: 'stard',
  moose: 'moose',
  arrive: 'arrive',
  // --- Phase 5b: health economics concepts ---
  cer: 'cost-effectiveness-ratio',
  'cost-effectiveness-ratio': 'cost-effectiveness-ratio',
  icer: 'incremental-cost-effectiveness-ratio',
  'incremental-cost-effectiveness-ratio': 'incremental-cost-effectiveness-ratio',
  qaly: 'quality-adjusted-life-year',
  'quality-adjusted-life-year': 'quality-adjusted-life-year',
  daly: 'disability-adjusted-life-year',
  'disability-adjusted-life-year': 'disability-adjusted-life-year',
  nmb: 'net-monetary-benefit',
  'net-monetary-benefit': 'net-monetary-benefit',
  cua: 'cost-utility-analysis',
  'cost-utility-analysis': 'cost-utility-analysis',
  ceac: 'cost-effectiveness-acceptability-curve',
  'cost-effectiveness-acceptability-curve': 'cost-effectiveness-acceptability-curve',
  markov: 'markov-model',
  'markov-model': 'markov-model',
  psa: 'probabilistic-sensitivity-analysis',
  'probabilistic-sensitivity-analysis': 'probabilistic-sensitivity-analysis',
  wtp: 'willingness-to-pay-threshold',
  'willingness-to-pay-threshold': 'willingness-to-pay-threshold',
  // --- Phase 5b: submission topics ---
  'picking-a-journal': 'picking-a-journal',
  'authorship-criteria': 'authorship-criteria',
  'cover-letter': 'cover-letter',
  'response-to-reviewers': 'response-to-reviewers',
  'conflict-of-interest': 'conflict-of-interest',
  'data-sharing-statements': 'data-sharing-statements',
  'copyright-and-licensing': 'copyright-and-licensing',
  preprints: 'preprints',
  registration: 'registration',
  'rejection-and-appeal': 'rejection-and-appeal',
  'reporting-guideline-selection': 'reporting-guideline-selection',
})

/**
 * Normalise a concept name to a Learn slug, then format it as a URL with
 * a `?slug=<slug>` query string. Returns the bare `/learn?slug=<slug>`
 * path; callers (e.g. <Link>) decide whether to prefix it with the
 * current project's route.
 *
 * If the concept is not in the alias table we still return a link —
 * callers can decide to render or hide the tooltip based on
 * `isKnownLearnConcept`.
 */
export function getLearnLink(concept: string): string {
  const slug = resolveLearnSlug(concept)
  return `${LEARN_BASE_PATH}?slug=${encodeURIComponent(slug)}`
}

/**
 * Public predicate — true when the concept resolves to a known Learn
 * slug. Use this to decide whether to render a contextual link.
 */
export function isKnownLearnConcept(concept: string): boolean {
  const key = normaliseKey(concept)
  return key in LEARN_CONCEPT_INDEX
}

/**
 * Resolve a friendly concept name to its canonical slug, falling back to
 * the (kebab-cased) input if the alias is unknown.
 */
export function resolveLearnSlug(concept: string): string {
  const key = normaliseKey(concept)
  if (key in LEARN_CONCEPT_INDEX) return LEARN_CONCEPT_INDEX[key]
  // Last resort — kebab-case the input so a bare "Mann Whitney" still
  // produces a deterministic URL even before we add the alias.
  return key
}

function normaliseKey(s: string): string {
  return s
    .trim()
    .toLowerCase()
    .replace(/['']/g, '')
    .replace(/[\s_]+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}
