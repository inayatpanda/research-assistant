import axios, { AxiosError } from 'axios'
import { z } from 'zod'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8787'

export const api = axios.create({
  baseURL: API_URL,
  timeout: 30_000,
})

/**
 * Coerce the FastAPI / generic JSON error body into a human string.
 *
 * Sources we try, in order:
 *   1. `body.detail` if string → use directly.
 *   2. `body.detail` if list of `{msg, loc}` (Pydantic validation) → join
 *      messages with semicolons; format the field path if `loc` is set.
 *   3. `body.message` (some endpoints use this shape) → use directly.
 *   4. Stringified body if compact JSON object.
 *   5. Axios's `error.message`.
 *   6. Generic `'Request failed'` fallback.
 */
function extractErrorMessage(error: AxiosError): string {
  const data = error.response?.data
  if (data && typeof data === 'object') {
    const body = data as Record<string, unknown>
    const detail = body.detail
    if (typeof detail === 'string' && detail.length > 0) return detail
    if (Array.isArray(detail) && detail.length > 0) {
      const parts: string[] = []
      for (const d of detail) {
        if (typeof d === 'string') {
          parts.push(d)
        } else if (d && typeof d === 'object' && 'msg' in d) {
          const obj = d as { msg?: unknown; loc?: unknown }
          const msg = typeof obj.msg === 'string' ? obj.msg : ''
          const loc = Array.isArray(obj.loc)
            ? obj.loc.filter((x) => typeof x === 'string' || typeof x === 'number').join('.')
            : ''
          parts.push(loc ? `${loc}: ${msg}` : msg)
        }
      }
      const joined = parts.filter(Boolean).join('; ')
      if (joined.length > 0) return joined
    }
    if (typeof body.message === 'string' && body.message.length > 0) {
      return body.message
    }
  }
  if (typeof data === 'string' && data.length > 0) return data
  if (error.response) {
    const status = error.response.status
    const statusText = error.response.statusText || 'Request failed'
    return `${status} ${statusText}`
  }
  if (error.message && error.message !== 'Network Error') return error.message
  return 'Request failed'
}

api.interceptors.response.use(
  (r) => r,
  (error: AxiosError) => Promise.reject(new Error(extractErrorMessage(error))),
)

// --- Schemas (runtime + types) ---

/** The 3 styles persistable on a project (server enforces).
 * Bibliography fetching additionally accepts `ieee` as a transient override. */
export const PersistedCitationStyleSchema = z.enum(['vancouver', 'apa', 'harvard'])
export type PersistedCitationStyle = z.infer<typeof PersistedCitationStyleSchema>

/** All styles supported by the bibliography endpoint + client-side formatters. */
export const CitationStyleSchema = z.enum(['vancouver', 'apa', 'harvard', 'ieee'])
export type CitationStyle = z.infer<typeof CitationStyleSchema>

export const ProjectSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  title: z.string(),
  study_type: z.string(),
  citation_style: PersistedCitationStyleSchema,
  ai_provider: z.enum(['gemini', 'claude', 'openai']),
  target_journal: z.string().nullable(),
  prospero_number: z.string().nullable(),
  clinicaltrials_number: z.string().nullable(),
  template_journal: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type Project = z.infer<typeof ProjectSchema>

export const ProjectCreateSchema = z.object({
  title: z.string().min(1).max(500),
  study_type: z.enum([
    'Before/After Intervention',
    'Outcome Study',
    'Risk Factor Analysis',
    'Group Comparison',
    'Prospective Cohort',
    'Retrospective Case Series',
    'Systematic Review',
    'Randomised Controlled Trial',
  ]),
  citation_style: PersistedCitationStyleSchema.optional(),
  ai_provider: z.enum(['gemini', 'claude', 'openai']).optional(),
  target_journal: z.string().optional(),
  prospero_number: z.string().optional(),
  clinicaltrials_number: z.string().optional(),
})
export type ProjectCreate = z.infer<typeof ProjectCreateSchema>

export const ProjectUpdateSchema = z.object({
  title: z.string().min(1).max(500).optional(),
  citation_style: PersistedCitationStyleSchema.optional(),
  ai_provider: z.enum(['gemini', 'claude', 'openai']).optional(),
  target_journal: z.string().nullable().optional(),
  prospero_number: z.string().nullable().optional(),
  clinicaltrials_number: z.string().nullable().optional(),
  template_journal: z.string().nullable().optional(),
})
export type ProjectUpdate = z.infer<typeof ProjectUpdateSchema>

export const HealthSchema = z.object({
  status: z.enum(['ok', 'degraded', 'down']),
  version: z.string(),
  db_ok: z.boolean(),
  storage_backend: z.string(),
  ai_providers: z.record(
    z.string(),
    z.object({
      ok: z.boolean(),
      active_model: z.string().nullable().optional(),
      reason: z.string().nullable().optional(),
    }),
  ),
})
export type Health = z.infer<typeof HealthSchema>

// --- Endpoints ---

export const projectsApi = {
  list: async (): Promise<Project[]> => {
    const r = await api.get('/api/projects')
    return z.array(ProjectSchema).parse(r.data)
  },
  get: async (id: string): Promise<Project> => {
    const r = await api.get(`/api/projects/${id}`)
    return ProjectSchema.parse(r.data)
  },
  create: async (data: ProjectCreate): Promise<Project> => {
    const r = await api.post('/api/projects', data)
    return ProjectSchema.parse(r.data)
  },
  update: async (id: string, patch: ProjectUpdate): Promise<Project> => {
    const r = await api.patch(`/api/projects/${id}`, patch)
    return ProjectSchema.parse(r.data)
  },
  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/projects/${id}`)
  },
}

export const metaApi = {
  health: async (): Promise<Health> => {
    const r = await api.get('/health')
    return HealthSchema.parse(r.data)
  },
}

// --- Articles ---

const StorageRefSchema = z.object({ backend: z.string(), key: z.string() })

export const ReviewStatusSchema = z.enum(['pending', 'included', 'excluded', 'unsure'])
export type ReviewStatus = z.infer<typeof ReviewStatusSchema>

export const ArticleSortSchema = z.enum(['created_desc', 'year_desc', 'year_asc', 'title'])
export type ArticleSort = z.infer<typeof ArticleSortSchema>

/** Provenance of an Article row. Phase 8.6 — every ingest surface stamps a value. */
export const ArticleSourceSchema = z.enum([
  'upload',
  'doi',
  'pubmed',
  'ris',
  'bibtex',
  'manual',
])
export type ArticleSource = z.infer<typeof ArticleSourceSchema>

export const ArticleSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  project_id: z.string(),
  title: z.string(),
  authors: z.array(z.string()),
  journal: z.string().nullable(),
  year: z.number().int().nullable(),
  volume: z.string().nullable(),
  issue: z.string().nullable(),
  pages: z.string().nullable(),
  doi: z.string().nullable(),
  pmid: z.string().nullable().optional(),
  file_ref: StorageRefSchema.nullable(),
  file_type: z.string().nullable(),
  abstract: z.string().nullable().optional(),
  study_design: z.string().nullable(),
  review_status: ReviewStatusSchema,
  exclusion_reason: z.string().nullable(),
  conflict_of_interest: z.string().nullable(),
  source: ArticleSourceSchema.default('upload'),
  created_at: z.string(),
  file_url: z.string().nullable().optional(),
})
export type Article = z.infer<typeof ArticleSchema>

export const ArticleUpdateSchema = z.object({
  title: z.string().min(1).max(1000).optional(),
  authors: z.array(z.string()).optional(),
  journal: z.string().optional().nullable(),
  year: z.number().int().min(1500).max(2200).optional().nullable(),
  volume: z.string().optional().nullable(),
  issue: z.string().optional().nullable(),
  pages: z.string().optional().nullable(),
  doi: z.string().optional().nullable(),
  study_design: z.string().optional().nullable(),
  review_status: ReviewStatusSchema.optional(),
  exclusion_reason: z.string().optional().nullable(),
  conflict_of_interest: z.string().optional().nullable(),
})
export type ArticleUpdate = z.infer<typeof ArticleUpdateSchema>

export const UploadResponseSchema = z.object({
  article: ArticleSchema,
  duplicate_of: ArticleSchema.nullable(),
  extraction_source: z.enum(['ai', 'crossref', 'both', 'none']),
  extraction_error: z.string().nullable(),
})
export type UploadResponse = z.infer<typeof UploadResponseSchema>

export type ArticleFilters = {
  q?: string
  review_status?: ReviewStatus
  study_design?: string
  sort?: ArticleSort
}

export const articlesApi = {
  list: async (projectId: string, filters: ArticleFilters = {}): Promise<Article[]> => {
    const r = await api.get(`/api/projects/${projectId}/articles`, { params: filters })
    return z.array(ArticleSchema).parse(r.data)
  },
  upload: async (projectId: string, file: File): Promise<UploadResponse> => {
    const fd = new FormData()
    fd.append('file', file)
    // Do NOT set Content-Type manually: the browser injects the proper
    // multipart boundary automatically when the body is a FormData
    // instance. Setting it explicitly (a) strips the boundary and breaks
    // parsing on the server, and (b) forces a CORS preflight.
    const r = await api.post(`/api/projects/${projectId}/articles/upload`, fd, {
      timeout: 120_000,
    })
    return UploadResponseSchema.parse(r.data)
  },
  get: async (id: string): Promise<Article> => {
    const r = await api.get(`/api/articles/${id}`)
    return ArticleSchema.parse(r.data)
  },
  update: async (id: string, patch: ArticleUpdate): Promise<Article> => {
    const r = await api.patch(`/api/articles/${id}`, patch)
    return ArticleSchema.parse(r.data)
  },
  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/articles/${id}`)
  },
}

// Resolve a file URL against the API base for cross-origin fetching
export function absoluteFileUrl(relativeUrl: string | null | undefined): string | null {
  if (!relativeUrl) return null
  if (relativeUrl.startsWith('http')) return relativeUrl
  return `${API_URL}${relativeUrl}`
}

// --- Highlights ---

export const HighlightColourSchema = z.enum(['intro', 'method', 'results', 'discussion'])
export type HighlightColour = z.infer<typeof HighlightColourSchema>

export const SectionNameSchema = z.enum([
  'Introduction',
  'Methodology',
  'Results',
  'Discussion',
])
export type SectionName = z.infer<typeof SectionNameSchema>

export const BoundingRectSchema = z.object({
  x0: z.number().min(0).max(1),
  y0: z.number().min(0).max(1),
  x1: z.number().min(0).max(1),
  y1: z.number().min(0).max(1),
})
export const BoundingCoordsSchema = z.object({
  rects: z.array(BoundingRectSchema).min(1),
})
export type BoundingRect = z.infer<typeof BoundingRectSchema>
export type BoundingCoords = z.infer<typeof BoundingCoordsSchema>

export const HighlightSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  article_id: z.string(),
  page_number: z.number().int(),
  selected_text: z.string(),
  colour: HighlightColourSchema,
  section: SectionNameSchema,
  bounding_coords: BoundingCoordsSchema,
  user_note: z.string().nullable(),
  ai_summary: z.string().nullable(),
  sort_order: z.number().int(),
  created_at: z.string(),
})
export type Highlight = z.infer<typeof HighlightSchema>

export type HighlightCreate = {
  page_number: number
  selected_text: string
  colour: HighlightColour
  section: SectionName
  bounding_coords: BoundingCoords
  user_note?: string | null
  sort_order?: number
}

export type HighlightUpdate = {
  user_note?: string | null
  ai_summary?: string | null
  sort_order?: number
}

export const highlightsApi = {
  list: async (articleId: string): Promise<Highlight[]> => {
    const r = await api.get(`/api/articles/${articleId}/highlights`)
    return z.array(HighlightSchema).parse(r.data)
  },
  create: async (articleId: string, body: HighlightCreate): Promise<Highlight> => {
    const r = await api.post(`/api/articles/${articleId}/highlights`, body)
    return HighlightSchema.parse(r.data)
  },
  update: async (id: string, patch: HighlightUpdate): Promise<Highlight> => {
    const r = await api.patch(`/api/highlights/${id}`, patch)
    return HighlightSchema.parse(r.data)
  },
  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/highlights/${id}`)
  },
  summarise: async (id: string): Promise<Highlight> => {
    const r = await api.post(`/api/highlights/${id}/summarise`)
    return HighlightSchema.parse(r.data)
  },
}

// --- Article general notes ---

export const ArticleNoteSchema = z.object({
  id: z.string().nullable(),
  user_id: z.string(),
  article_id: z.string(),
  content: z.string(),
  updated_at: z.string().nullable(),
})
export type ArticleNote = z.infer<typeof ArticleNoteSchema>

export const notesApi = {
  get: async (articleId: string): Promise<ArticleNote> => {
    const r = await api.get(`/api/articles/${articleId}/notes`)
    return ArticleNoteSchema.parse(r.data)
  },
  upsert: async (articleId: string, content: string): Promise<ArticleNote> => {
    const r = await api.put(`/api/articles/${articleId}/notes`, { content })
    return ArticleNoteSchema.parse(r.data)
  },
}

// --- Compilation ---

export const CompiledCardSchema = z.object({
  highlight_id: z.string(),
  article_id: z.string(),
  citation: z.string(),
  article_title: z.string(),
  article_authors: z.array(z.string()),
  article_year: z.number().int().nullable(),
  article_journal: z.string().nullable(),
  article_doi: z.string().nullable(),
  page_number: z.number().int(),
  selected_text: z.string(),
  user_note: z.string().nullable(),
  ai_summary: z.string().nullable(),
  section: SectionNameSchema,
  colour: HighlightColourSchema,
  sort_order: z.number().int(),
})
export type CompiledCard = z.infer<typeof CompiledCardSchema>

export const CompilationViewSchema = z.object({
  project_id: z.string(),
  colour: HighlightColourSchema,
  section: SectionNameSchema,
  cards: z.array(CompiledCardSchema),
})
export type CompilationView = z.infer<typeof CompilationViewSchema>

export const CardDraftResponseSchema = z.object({
  highlight_id: z.string(),
  draft: z.string(),
  used_citation: z.string(),
})
export type CardDraftResponse = z.infer<typeof CardDraftResponseSchema>

export const SectionDraftResponseSchema = z.object({
  project_id: z.string(),
  colour: HighlightColourSchema,
  section: SectionNameSchema,
  draft: z.string(),
  used_citations: z.array(z.string()),
})
export type SectionDraftResponse = z.infer<typeof SectionDraftResponseSchema>

export const compilationApi = {
  view: async (projectId: string, colour: HighlightColour): Promise<CompilationView> => {
    const r = await api.get(`/api/projects/${projectId}/compilation/${colour}`)
    return CompilationViewSchema.parse(r.data)
  },
  cardDraft: async (highlightId: string): Promise<CardDraftResponse> => {
    const r = await api.post(`/api/highlights/${highlightId}/draft`, {}, { timeout: 60_000 })
    return CardDraftResponseSchema.parse(r.data)
  },
  sectionDraft: async (
    projectId: string,
    colour: HighlightColour,
  ): Promise<SectionDraftResponse> => {
    const r = await api.post(
      `/api/projects/${projectId}/compilation/${colour}/draft`,
      {},
      { timeout: 90_000 },
    )
    return SectionDraftResponseSchema.parse(r.data)
  },
  reorder: async (
    projectId: string,
    colour: HighlightColour,
    items: Array<{ highlight_id: string; sort_order: number }>,
  ): Promise<CompilationView> => {
    const r = await api.patch(
      `/api/projects/${projectId}/compilation/${colour}/order`,
      { items },
    )
    return CompilationViewSchema.parse(r.data)
  },
}

// --- Manuscript sections ---

export const ManuscriptSectionNameSchema = z.enum([
  'Introduction',
  'Methodology',
  'Results',
  'Discussion',
  'Abstract',
  'Conclusion',
])
export type ManuscriptSectionName = z.infer<typeof ManuscriptSectionNameSchema>

export const ManuscriptSectionSchema = z.object({
  id: z.string().nullable(),
  user_id: z.string(),
  project_id: z.string(),
  section_name: ManuscriptSectionNameSchema,
  content: z.string(),
  word_count: z.number().int(),
  updated_at: z.string().nullable(),
})
export type ManuscriptSection = z.infer<typeof ManuscriptSectionSchema>

export const manuscriptApi = {
  getSection: async (
    projectId: string,
    section: ManuscriptSectionName,
  ): Promise<ManuscriptSection> => {
    const r = await api.get(`/api/projects/${projectId}/sections/${section}`)
    return ManuscriptSectionSchema.parse(r.data)
  },
  upsertSection: async (
    projectId: string,
    section: ManuscriptSectionName,
    content: string,
  ): Promise<ManuscriptSection> => {
    const r = await api.put(`/api/projects/${projectId}/sections/${section}`, {
      section_name: section,
      content,
    })
    return ManuscriptSectionSchema.parse(r.data)
  },
}

// --- Writing assist ---

export const WritingActionSchema = z.enum(['improve', 'shorten', 'formalise', 'add_transition'])
export type WritingAction = z.infer<typeof WritingActionSchema>

export const WritingAssistResponseSchema = z.object({ revised: z.string() })

export const writingApi = {
  assist: async (action: WritingAction, text: string): Promise<string> => {
    const r = await api.post('/api/writing/assist', { action, text }, { timeout: 60_000 })
    return WritingAssistResponseSchema.parse(r.data).revised
  },
}

// --- Abbreviations ---

export const AbbreviationItemSchema = z.object({
  short_form: z.string().min(1).max(32),
  long_form: z.string().min(1).max(500),
})
export type AbbreviationItem = z.infer<typeof AbbreviationItemSchema>

export const AbbreviationSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  project_id: z.string(),
  short_form: z.string(),
  long_form: z.string(),
  created_at: z.string(),
})
export type Abbreviation = z.infer<typeof AbbreviationSchema>

export const abbreviationsApi = {
  list: async (projectId: string): Promise<Abbreviation[]> => {
    const r = await api.get(`/api/projects/${projectId}/abbreviations`)
    return z.array(AbbreviationSchema).parse(r.data)
  },
  replace: async (projectId: string, items: AbbreviationItem[]): Promise<Abbreviation[]> => {
    const r = await api.put(`/api/projects/${projectId}/abbreviations`, { items })
    return z.array(AbbreviationSchema).parse(r.data)
  },
  delete: async (id: string): Promise<void> => {
    await api.delete(`/api/abbreviations/${id}`)
  },
}

// --- Datasets ---

export const VariableTypeSchema = z.enum([
  'numeric',
  'ordinal',
  'nominal',
  'time',
  'event_indicator',
  'unknown',
])
export type VariableType = z.infer<typeof VariableTypeSchema>

export const DatasetVariableSchema = z.object({
  id: z.string(),
  dataset_id: z.string(),
  name: z.string(),
  position: z.number().int(),
  inferred_type: VariableTypeSchema,
  user_type: VariableTypeSchema.nullable(),
  n_missing: z.number().int(),
  sample_values: z.array(z.string()),
  instrument_key: z.string().nullable().optional(),
  // DEMO-FIX-C — Free-text label used for chart axes, AI prose and exports.
  // Falls back to the canonical ``name`` when unset.
  display_label: z.string().nullable().optional(),
})
export type DatasetVariable = z.infer<typeof DatasetVariableSchema>

export const HeaderSanitisationEntrySchema = z.object({
  original: z.string(),
  sanitised: z.string(),
})
export type HeaderSanitisationEntry = z.infer<
  typeof HeaderSanitisationEntrySchema
>

export const DatasetSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  filename: z.string(),
  file_type: z.string(),
  n_rows: z.number().int(),
  n_columns: z.number().int(),
  created_at: z.string(),
  variables: z.array(DatasetVariableSchema),
  derived_from_dataset_id: z.string().nullable().optional(),
  derived_from_dataset_ids: z.array(z.string()).nullable().optional(),
  dataset_metadata: z
    .record(z.string(), z.unknown())
    .nullable()
    .optional(),
  // DEMO-FIX-C — Non-empty on the upload response when at least one raw
  // header was sanitised. Each entry: { original, sanitised }.
  header_sanitisation_report: z
    .array(HeaderSanitisationEntrySchema)
    .optional()
    .default([]),
})
export type Dataset = z.infer<typeof DatasetSchema>

export const datasetsApi = {
  list: async (projectId: string): Promise<Dataset[]> => {
    const r = await api.get(`/api/projects/${projectId}/datasets`)
    return z.array(DatasetSchema).parse(r.data)
  },
  get: async (projectId: string, datasetId: string): Promise<Dataset> => {
    const r = await api.get(`/api/projects/${projectId}/datasets/${datasetId}`)
    return DatasetSchema.parse(r.data)
  },
  upload: async (projectId: string, file: File): Promise<Dataset> => {
    const fd = new FormData()
    fd.append('file', file)
    // Do NOT set Content-Type manually: fetch/axios attach the correct
    // multipart boundary automatically when the body is FormData. Setting
    // it explicitly drops the boundary AND forces a CORS preflight.
    const r = await api.post(`/api/projects/${projectId}/datasets`, fd, {
      timeout: 120_000,
    })
    return DatasetSchema.parse(r.data)
  },
  delete: async (projectId: string, datasetId: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/datasets/${datasetId}`)
  },
  updateVariable: async (
    projectId: string,
    datasetId: string,
    variableId: string,
    userType: VariableType | null,
  ): Promise<DatasetVariable> => {
    const r = await api.patch(
      `/api/projects/${projectId}/datasets/${datasetId}/variables/${variableId}`,
      { user_type: userType },
    )
    return DatasetVariableSchema.parse(r.data)
  },
  /** DEMO-FIX-C — Update the free-text display label on a variable. */
  updateVariableDisplayLabel: async (
    projectId: string,
    datasetId: string,
    variableId: string,
    displayLabel: string,
  ): Promise<DatasetVariable> => {
    const r = await api.patch(
      `/api/projects/${projectId}/datasets/${datasetId}/variables/${variableId}/display-label`,
      { display_label: displayLabel },
    )
    return DatasetVariableSchema.parse(r.data)
  },
  preview: async (
    projectId: string,
    datasetId: string,
    offset = 0,
    limit = 50,
  ): Promise<{
    columns: string[]
    rows: Array<Record<string, unknown> & { __row_index: number }>
    offset: number
    limit: number
    total: number
  }> => {
    const r = await api.get(
      `/api/projects/${projectId}/datasets/${datasetId}/data`,
      { params: { offset, limit } },
    )
    return r.data
  },
}

// --- Analyses ---

export const QuestionTypeSchema = z.enum([
  'group_comparison',
  'association',
  'time_to_event',
  'agreement',
])
export type QuestionType = z.infer<typeof QuestionTypeSchema>

export const TestKeySchema = z.enum([
  'independent_t',
  'paired_t',
  'mann_whitney',
  'wilcoxon_signed',
  'chi_squared',
  'fisher_exact',
  'one_way_anova',
  'kruskal_wallis',
  'rm_anova',
  'pearson',
  'spearman',
  'linear_regression',
  'multiple_linear',
  'logistic',
  'kaplan_meier',
  'cox_ph',
  'icc',
  'cohen_kappa',
  // Phase 13 (MP13) — extended catalogue.
  'mixed_effects_lm',
  'glm_poisson',
  'glm_binomial',
  'glm_gamma',
  'gee',
  'bootstrap_mean_diff',
  'permutation_test',
  'tost_equivalence',
  'tost_noninferiority',
])
export type TestKey = z.infer<typeof TestKeySchema>

export const AnalysisStatusSchema = z.enum([
  'draft',
  'ready',
  'running',
  'completed',
  'failed',
])
export type AnalysisStatus = z.infer<typeof AnalysisStatusSchema>

export const RecommendationResponseSchema = z.object({
  chosen_test: TestKeySchema,
  rationale: z.string(),
  assumption_warnings: z.array(z.string()),
})
export type RecommendationResponse = z.infer<typeof RecommendationResponseSchema>

export type RecommendationRequest = {
  question_type: QuestionType
  variables: Record<string, string | string[]>
}

export const AnalysisResultSchema = z.object({
  summary: z.record(z.string(), z.any()),
  assumptions: z.record(z.string(), z.any()),
  chart: z.record(z.string(), z.any()).nullable(),
  ai_interpretation: z.string().nullable(),
})
export type AnalysisResult = z.infer<typeof AnalysisResultSchema>

export const AnalysisSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  dataset_id: z.string(),
  question_type: QuestionTypeSchema,
  chosen_test: TestKeySchema,
  recommendation_rationale: z.string(),
  variables: z.record(z.string(), z.any()),
  status: AnalysisStatusSchema,
  created_at: z.string(),
  result: AnalysisResultSchema.nullable().optional(),
})
export type Analysis = z.infer<typeof AnalysisSchema>

export type AnalysisCreate = {
  question_type: QuestionType
  chosen_test: TestKey
  variables: Record<string, unknown>
}

export const TEST_LABELS: Record<TestKey, string> = {
  independent_t: 'Independent t-test',
  paired_t: 'Paired t-test',
  mann_whitney: 'Mann–Whitney U',
  wilcoxon_signed: 'Wilcoxon signed-rank',
  chi_squared: 'Chi-squared test',
  fisher_exact: "Fisher's exact test",
  one_way_anova: 'One-way ANOVA',
  kruskal_wallis: 'Kruskal–Wallis',
  rm_anova: 'Repeated-measures ANOVA',
  pearson: 'Pearson correlation',
  spearman: 'Spearman correlation',
  linear_regression: 'Linear regression',
  multiple_linear: 'Multiple linear regression',
  logistic: 'Logistic regression',
  kaplan_meier: 'Kaplan–Meier',
  cox_ph: 'Cox proportional hazards',
  icc: 'Intraclass correlation',
  cohen_kappa: "Cohen's kappa",
  mixed_effects_lm: 'Mixed-effects linear model',
  glm_poisson: 'GLM (Poisson)',
  glm_binomial: 'GLM (Binomial)',
  glm_gamma: 'GLM (Gamma)',
  gee: 'Generalized estimating equations',
  bootstrap_mean_diff: 'Bootstrap (mean difference)',
  permutation_test: 'Permutation test',
  tost_equivalence: 'TOST equivalence',
  tost_noninferiority: 'TOST non-inferiority',
}

export const analysesApi = {
  recommend: async (
    projectId: string,
    datasetId: string,
    body: RecommendationRequest,
  ): Promise<RecommendationResponse> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/analyses/recommend`,
      body,
      { timeout: 60_000 },
    )
    return RecommendationResponseSchema.parse(r.data)
  },
  create: async (
    projectId: string,
    datasetId: string,
    body: AnalysisCreate,
  ): Promise<Analysis> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/analyses`,
      body,
    )
    return AnalysisSchema.parse(r.data)
  },
  listForDataset: async (
    projectId: string,
    datasetId: string,
  ): Promise<Analysis[]> => {
    const r = await api.get(
      `/api/projects/${projectId}/datasets/${datasetId}/analyses`,
    )
    return z.array(AnalysisSchema).parse(r.data)
  },
  get: async (projectId: string, analysisId: string): Promise<Analysis> => {
    const r = await api.get(`/api/projects/${projectId}/analyses/${analysisId}`)
    return AnalysisSchema.parse(r.data)
  },
  run: async (projectId: string, analysisId: string): Promise<Analysis> => {
    const r = await api.post(
      `/api/projects/${projectId}/analyses/${analysisId}/run`,
      {},
      { timeout: 90_000 },
    )
    return AnalysisSchema.parse(r.data)
  },
  interpret: async (projectId: string, analysisId: string): Promise<Analysis> => {
    const r = await api.post(
      `/api/projects/${projectId}/analyses/${analysisId}/interpret`,
      {},
      { timeout: 60_000 },
    )
    return AnalysisSchema.parse(r.data)
  },
  pushToManuscript: async (
    projectId: string,
    analysisId: string,
  ): Promise<ManuscriptSection> => {
    const r = await api.post(
      `/api/projects/${projectId}/analyses/${analysisId}/push`,
      {},
    )
    return ManuscriptSectionSchema.parse(r.data)
  },
  delete: async (projectId: string, analysisId: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/analyses/${analysisId}`)
  },
  /** DEMO-FIX-C — Set per-chart x/y/title label overrides and re-render. */
  updateChartLabels: async (
    projectId: string,
    analysisId: string,
    body: {
      x_label_override?: string | null
      y_label_override?: string | null
      title_override?: string | null
    },
  ): Promise<Analysis> => {
    const r = await api.patch(
      `/api/projects/${projectId}/analyses/${analysisId}/chart-labels`,
      body,
      { timeout: 60_000 },
    )
    return AnalysisSchema.parse(r.data)
  },
}

// --- Reviews (Systematic Review) ---

export const ReviewStageSchema = z.enum(['title_abstract', 'full_text'])
export type ReviewStage = z.infer<typeof ReviewStageSchema>

export const ScreeningDecisionSchema = z.enum([
  'pending',
  'include',
  'exclude',
  'maybe',
])
export type ScreeningDecision = z.infer<typeof ScreeningDecisionSchema>

export const ExclusionCategorySchema = z.enum([
  'population',
  'intervention',
  'outcome',
  'study_design',
  'language',
  'duplicate',
  'other',
])
export type ExclusionCategory = z.infer<typeof ExclusionCategorySchema>

export const RoBToolSchema = z.enum(['rob2', 'robins_i', 'nos', 'amstar2'])
export type RoBTool = z.infer<typeof RoBToolSchema>

export const RoBJudgementSchema = z.enum([
  'low',
  'some_concerns',
  'high',
  'critical',
  'unclear',
])
export type RoBJudgement = z.infer<typeof RoBJudgementSchema>

export const DatabaseNameSchema = z.enum([
  'PubMed',
  'Embase',
  'Cochrane',
  'Scopus',
  'Web of Science',
  'Google Scholar',
  'Other',
])
export type DatabaseName = z.infer<typeof DatabaseNameSchema>

export const ROB_TOOL_LABELS: Record<RoBTool, string> = {
  rob2: 'RoB 2 (RCTs)',
  robins_i: 'ROBINS-I (non-randomised)',
  nos: 'Newcastle-Ottawa (cohort)',
  amstar2: 'AMSTAR-2 (reviews)',
}

export const ROB_JUDGEMENT_LABELS: Record<RoBJudgement, string> = {
  low: 'Low',
  some_concerns: 'Some concerns',
  high: 'High',
  critical: 'Critical',
  unclear: 'Unclear',
}

export const EXCLUSION_CATEGORY_LABELS: Record<ExclusionCategory, string> = {
  population: 'Wrong population',
  intervention: 'Wrong intervention',
  outcome: 'Wrong outcome',
  study_design: 'Wrong study design',
  language: 'Language',
  duplicate: 'Duplicate',
  other: 'Other',
}

export const SCREENING_DECISION_LABELS: Record<ScreeningDecision, string> = {
  pending: 'Pending',
  include: 'Include',
  exclude: 'Exclude',
  maybe: 'Maybe',
}

// Review (PICO + eligibility)

export const ReviewSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  pico_population: z.string().nullable(),
  pico_intervention: z.string().nullable(),
  pico_comparator: z.string().nullable(),
  pico_outcome: z.string().nullable(),
  eligibility_inclusion: z.string().nullable(),
  eligibility_exclusion: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type Review = z.infer<typeof ReviewSchema>

export const ReviewUpdateSchema = z.object({
  pico_population: z.string().nullable().optional(),
  pico_intervention: z.string().nullable().optional(),
  pico_comparator: z.string().nullable().optional(),
  pico_outcome: z.string().nullable().optional(),
  eligibility_inclusion: z.string().nullable().optional(),
  eligibility_exclusion: z.string().nullable().optional(),
})
export type ReviewUpdate = z.infer<typeof ReviewUpdateSchema>

// Search records

export const SearchRecordSchema = z.object({
  id: z.string(),
  review_id: z.string(),
  database_name: z.string(),
  query_string: z.string(),
  date_searched: z.string(),
  n_results: z.number().int(),
  notes: z.string().nullable(),
  created_at: z.string(),
})
export type SearchRecord = z.infer<typeof SearchRecordSchema>

export type SearchRecordCreate = {
  database_name: DatabaseName
  query_string: string
  date_searched: string // ISO datetime
  n_results: number
  notes?: string | null
}

export type SearchRecordUpdate = {
  database_name?: DatabaseName
  query_string?: string
  date_searched?: string
  n_results?: number
  notes?: string | null
}

// Screening

export const ScreeningRecordSchema = z.object({
  id: z.string(),
  review_id: z.string(),
  article_id: z.string(),
  stage: z.string(),
  decision: z.string(),
  exclusion_category: z.string().nullable(),
  reason: z.string().nullable(),
  reviewer_id: z.string().nullable(),
  ai_suggestion: z.record(z.string(), z.any()).nullable(),
  decided_at: z.string().nullable(),
  created_at: z.string(),
})
export type ScreeningRecord = z.infer<typeof ScreeningRecordSchema>

export type ScreeningRecordCreate = {
  article_id: string
  stage: ReviewStage
  decision?: ScreeningDecision
  exclusion_category?: ExclusionCategory | null
  reason?: string | null
}

export type ScreeningRecordUpdate = {
  decision?: ScreeningDecision
  exclusion_category?: ExclusionCategory | null
  reason?: string | null
}

export const AIScreeningSuggestResponseSchema = z.object({
  vote: ScreeningDecisionSchema,
  reason: z.string(),
  model: z.string(),
})
export type AIScreeningSuggestResponse = z.infer<
  typeof AIScreeningSuggestResponseSchema
>

// RoB

export const RoBDomainSchema = z.object({
  key: z.string(),
  label: z.string(),
  question: z.string(),
  answers: z.array(z.string()),
  critical: z.boolean(),
})
export type RoBDomain = z.infer<typeof RoBDomainSchema>

export const RoBToolDefSchema = z.object({
  key: z.string(),
  label: z.string(),
  applies_to: z.array(z.string()),
  domains: z.array(RoBDomainSchema),
})
export type RoBToolDef = z.infer<typeof RoBToolDefSchema>

export const RoBAssessmentSchema = z.object({
  id: z.string(),
  review_id: z.string(),
  article_id: z.string(),
  tool: z.string(),
  domain_answers: z.record(z.string(), z.string()),
  overall_auto: z.string(),
  overall_override: z.string().nullable(),
  notes: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type RoBAssessment = z.infer<typeof RoBAssessmentSchema>

export type RoBAssessmentCreate = {
  article_id: string
  tool: RoBTool
  domain_answers: Record<string, string>
  notes?: string | null
}

export type RoBAssessmentUpdate = {
  domain_answers?: Record<string, string>
  overall_override?: RoBJudgement | null
  notes?: string | null
}

// Extraction

export const ExtractionFieldTypeSchema = z.enum([
  'text',
  'number',
  'enum',
  'list',
])
export type ExtractionFieldType = z.infer<typeof ExtractionFieldTypeSchema>

export const ExtractionFieldSchema = z.object({
  key: z.string(),
  label: z.string(),
  type: ExtractionFieldTypeSchema,
  required: z.boolean(),
  choices: z.array(z.string()).nullable(),
  allow_negative: z.boolean().optional().default(false),
})
export type ExtractionField = z.infer<typeof ExtractionFieldSchema>

export const ExtractionFieldGroupSchema = z.object({
  key: z.string(),
  label: z.string(),
  fields: z.array(ExtractionFieldSchema),
})
export type ExtractionFieldGroup = z.infer<typeof ExtractionFieldGroupSchema>

export const ExtractionRecordSchema = z.object({
  id: z.string(),
  review_id: z.string(),
  article_id: z.string(),
  fields: z.record(z.string(), z.any()),
  created_at: z.string(),
  updated_at: z.string(),
})
export type ExtractionRecord = z.infer<typeof ExtractionRecordSchema>

export type ExtractionRecordCreate = {
  article_id: string
  fields: Record<string, unknown>
}

export type ExtractionRecordUpdate = {
  fields: Record<string, unknown>
}

// PRISMA

export const PrismaCountsSchema = z.object({
  identified: z.number().int(),
  after_dedupe: z.number().int(),
  screened: z.number().int(),
  excluded_title: z.number().int(),
  full_text_assessed: z.number().int(),
  excluded_full: z.record(z.string(), z.number().int()),
  included: z.number().int(),
})
export type PrismaCounts = z.infer<typeof PrismaCountsSchema>

export const PrismaResponseSchema = z.object({
  counts: PrismaCountsSchema,
  svg: z.string(),
})
export type PrismaResponse = z.infer<typeof PrismaResponseSchema>

// API namespaces

export const reviewsApi = {
  get: async (projectId: string): Promise<Review> => {
    const r = await api.get(`/api/projects/${projectId}/reviews`)
    return ReviewSchema.parse(r.data)
  },
  patch: async (projectId: string, body: ReviewUpdate): Promise<Review> => {
    const r = await api.patch(`/api/projects/${projectId}/reviews`, body)
    return ReviewSchema.parse(r.data)
  },
  prisma: async (projectId: string): Promise<PrismaResponse> => {
    const r = await api.get(`/api/projects/${projectId}/reviews/prisma`)
    return PrismaResponseSchema.parse(r.data)
  },
  pushPrisma: async (projectId: string): Promise<ManuscriptSection> => {
    const r = await api.post(
      `/api/projects/${projectId}/reviews/prisma/push`,
      {},
    )
    return ManuscriptSectionSchema.parse(r.data)
  },
}

export const searchApi = {
  list: async (projectId: string): Promise<SearchRecord[]> => {
    const r = await api.get(`/api/projects/${projectId}/reviews/search`)
    return z.array(SearchRecordSchema).parse(r.data)
  },
  create: async (
    projectId: string,
    body: SearchRecordCreate,
  ): Promise<SearchRecord> => {
    const r = await api.post(`/api/projects/${projectId}/reviews/search`, body)
    return SearchRecordSchema.parse(r.data)
  },
  update: async (
    projectId: string,
    searchId: string,
    body: SearchRecordUpdate,
  ): Promise<SearchRecord> => {
    const r = await api.patch(
      `/api/projects/${projectId}/reviews/search/${searchId}`,
      body,
    )
    return SearchRecordSchema.parse(r.data)
  },
  remove: async (projectId: string, searchId: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/reviews/search/${searchId}`)
  },
  push: async (projectId: string): Promise<ManuscriptSection> => {
    const r = await api.post(
      `/api/projects/${projectId}/reviews/search/push`,
      {},
    )
    return ManuscriptSectionSchema.parse(r.data)
  },
}

export const screeningApi = {
  list: async (
    projectId: string,
    stage?: ReviewStage,
  ): Promise<ScreeningRecord[]> => {
    const r = await api.get(`/api/projects/${projectId}/reviews/screening`, {
      params: stage ? { stage } : undefined,
    })
    return z.array(ScreeningRecordSchema).parse(r.data)
  },
  upsert: async (
    projectId: string,
    body: ScreeningRecordCreate,
  ): Promise<ScreeningRecord> => {
    const r = await api.post(
      `/api/projects/${projectId}/reviews/screening`,
      body,
    )
    return ScreeningRecordSchema.parse(r.data)
  },
  update: async (
    projectId: string,
    screeningId: string,
    body: ScreeningRecordUpdate,
  ): Promise<ScreeningRecord> => {
    const r = await api.patch(
      `/api/projects/${projectId}/reviews/screening/${screeningId}`,
      body,
    )
    return ScreeningRecordSchema.parse(r.data)
  },
  remove: async (projectId: string, screeningId: string): Promise<void> => {
    await api.delete(
      `/api/projects/${projectId}/reviews/screening/${screeningId}`,
    )
  },
  aiSuggest: async (
    projectId: string,
    screeningId: string,
  ): Promise<AIScreeningSuggestResponse> => {
    const r = await api.post(
      `/api/projects/${projectId}/reviews/screening/${screeningId}/ai-suggest`,
      {},
      { timeout: 60_000 },
    )
    return AIScreeningSuggestResponseSchema.parse(r.data)
  },
}

export const robApi = {
  tools: async (projectId: string): Promise<RoBToolDef[]> => {
    const r = await api.get(`/api/projects/${projectId}/reviews/rob/tools`)
    return z.array(RoBToolDefSchema).parse(r.data)
  },
  list: async (projectId: string): Promise<RoBAssessment[]> => {
    const r = await api.get(`/api/projects/${projectId}/reviews/rob`)
    return z.array(RoBAssessmentSchema).parse(r.data)
  },
  upsert: async (
    projectId: string,
    body: RoBAssessmentCreate,
  ): Promise<RoBAssessment> => {
    const r = await api.post(`/api/projects/${projectId}/reviews/rob`, body)
    return RoBAssessmentSchema.parse(r.data)
  },
  update: async (
    projectId: string,
    robId: string,
    body: RoBAssessmentUpdate,
  ): Promise<RoBAssessment> => {
    const r = await api.patch(
      `/api/projects/${projectId}/reviews/rob/${robId}`,
      body,
    )
    return RoBAssessmentSchema.parse(r.data)
  },
  remove: async (projectId: string, robId: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/reviews/rob/${robId}`)
  },
  push: async (projectId: string): Promise<ManuscriptSection> => {
    const r = await api.post(`/api/projects/${projectId}/reviews/rob/push`, {})
    return ManuscriptSectionSchema.parse(r.data)
  },
}

export const extractionApi = {
  schema: async (projectId: string): Promise<ExtractionFieldGroup[]> => {
    const r = await api.get(
      `/api/projects/${projectId}/reviews/extraction/schema`,
    )
    return z.array(ExtractionFieldGroupSchema).parse(r.data)
  },
  list: async (projectId: string): Promise<ExtractionRecord[]> => {
    const r = await api.get(`/api/projects/${projectId}/reviews/extraction`)
    return z.array(ExtractionRecordSchema).parse(r.data)
  },
  upsert: async (
    projectId: string,
    body: ExtractionRecordCreate,
  ): Promise<ExtractionRecord> => {
    const r = await api.post(
      `/api/projects/${projectId}/reviews/extraction`,
      body,
    )
    return ExtractionRecordSchema.parse(r.data)
  },
  update: async (
    projectId: string,
    extId: string,
    body: ExtractionRecordUpdate,
  ): Promise<ExtractionRecord> => {
    const r = await api.patch(
      `/api/projects/${projectId}/reviews/extraction/${extId}`,
      body,
    )
    return ExtractionRecordSchema.parse(r.data)
  },
  remove: async (projectId: string, extId: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/reviews/extraction/${extId}`)
  },
  push: async (projectId: string): Promise<ManuscriptSection> => {
    const r = await api.post(
      `/api/projects/${projectId}/reviews/extraction/push`,
      {},
    )
    return ManuscriptSectionSchema.parse(r.data)
  },
}

// --- Bibliography ---

export const BibliographyEntrySchema = z.object({
  number: z.number().int(),
  article_id: z.string(),
  formatted_entry: z.string(),
  first_section: z.string(),
})
export type BibliographyEntry = z.infer<typeof BibliographyEntrySchema>

export const BibliographyResponseSchema = z.object({
  style: CitationStyleSchema,
  entries: z.array(BibliographyEntrySchema),
})
export type BibliographyResponse = z.infer<typeof BibliographyResponseSchema>

export const bibliographyApi = {
  get: async (projectId: string, style?: CitationStyle): Promise<BibliographyResponse> => {
    const r = await api.get(`/api/projects/${projectId}/bibliography`, {
      params: style ? { style } : undefined,
    })
    return BibliographyResponseSchema.parse(r.data)
  },
}

// --- Export / Import ---

export const BundleImportResponseSchema = z.object({
  project_id: z.string(),
  counts: z.record(z.string(), z.number().int()),
})
export type BundleImportResponse = z.infer<typeof BundleImportResponseSchema>

/** 50 MiB — must match the server-side cap in routes/export.py. */
export const IMPORT_SIZE_CAP_BYTES = 50 * 1024 * 1024

const FILENAME_STAR_RE = /filename\*\s*=\s*[^']*''([^;]+)/i
const FILENAME_RE = /filename\s*=\s*("([^"]+)"|([^;]+))/i

function parseContentDispositionFilename(header: string | null): string | null {
  if (!header) return null
  const starMatch = FILENAME_STAR_RE.exec(header)
  if (starMatch?.[1]) {
    try {
      return decodeURIComponent(starMatch[1].trim())
    } catch {
      // fall through
    }
  }
  const m = FILENAME_RE.exec(header)
  if (m) return (m[2] ?? m[3] ?? '').trim()
  return null
}

function todayStamp(): string {
  return new Date().toISOString().slice(0, 10)
}

function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.rel = 'noopener'
  document.body.appendChild(a)
  a.click()
  a.remove()
  // Defer to next tick — Safari needs the anchor to still be present briefly.
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

async function postForBlob(
  path: string,
  fallbackFilename: string,
): Promise<{ blob: Blob; filename: string }> {
  const r = await api.post(path, undefined, { responseType: 'blob' })
  const filename =
    parseContentDispositionFilename(
      (r.headers['content-disposition'] as string | undefined) ?? null,
    ) ?? fallbackFilename
  return { blob: r.data as Blob, filename }
}

export const exportApi = {
  downloadDocx: async (projectId: string, slug = 'manuscript'): Promise<string> => {
    const { blob, filename } = await postForBlob(
      `/api/projects/${projectId}/export/docx`,
      `${slug}-${todayStamp()}.docx`,
    )
    triggerBlobDownload(blob, filename)
    return filename
  },
  downloadPdf: async (projectId: string, slug = 'manuscript'): Promise<string> => {
    const { blob, filename } = await postForBlob(
      `/api/projects/${projectId}/export/pdf`,
      `${slug}-${todayStamp()}.pdf`,
    )
    triggerBlobDownload(blob, filename)
    return filename
  },
  downloadBundle: async (projectId: string, slug = 'manuscript'): Promise<string> => {
    const { blob, filename } = await postForBlob(
      `/api/projects/${projectId}/export/bundle`,
      `${slug}-bundle-${todayStamp()}.json`,
    )
    triggerBlobDownload(blob, filename)
    return filename
  },
  downloadSubmissionPackage: async (
    projectId: string,
    snapshotId?: string,
    slug = 'submission',
  ): Promise<string> => {
    const path = `/api/projects/${projectId}/export/submission-package`
    const r = await api.post(path, undefined, {
      responseType: 'blob',
      params: snapshotId ? { snapshot_id: snapshotId } : undefined,
    })
    const filename =
      parseContentDispositionFilename(
        (r.headers['content-disposition'] as string | undefined) ?? null,
      ) ?? `${slug}-${todayStamp()}.zip`
    triggerBlobDownload(r.data as Blob, filename)
    return filename
  },
  importBundle: async (file: File): Promise<BundleImportResponse> => {
    if (file.size > IMPORT_SIZE_CAP_BYTES) {
      throw new Error(
        `Bundle exceeds ${IMPORT_SIZE_CAP_BYTES / (1024 * 1024)} MiB cap (got ${(
          file.size /
          (1024 * 1024)
        ).toFixed(1)} MiB)`,
      )
    }
    const fd = new FormData()
    fd.append('file', file)
    // No explicit Content-Type — see articlesApi.upload for the rationale.
    const r = await api.post('/api/projects/import/bundle', fd, {
      timeout: 120_000,
    })
    return BundleImportResponseSchema.parse(r.data)
  },
}

// --- Meta-analysis (Phase 7.5) ---

export const EffectMetricSchema = z.enum(['md', 'smd', 'or', 'rr', 'hr', 'r'])
export type EffectMetric = z.infer<typeof EffectMetricSchema>

export const PoolingModelSchema = z.enum(['fixed', 'random'])
export type PoolingModel = z.infer<typeof PoolingModelSchema>

export const MetaStatusSchema = z.enum(['draft', 'running', 'completed', 'failed'])
export type MetaStatus = z.infer<typeof MetaStatusSchema>

export const MetaInputReadSchema = z.object({
  id: z.string(),
  meta_id: z.string(),
  article_id: z.string(),
  study_label: z.string().nullable(),
  subgroup: z.string().nullable(),
  mean_a: z.number().nullable(),
  sd_a: z.number().nullable(),
  n_a: z.number().int().nullable(),
  mean_b: z.number().nullable(),
  sd_b: z.number().nullable(),
  n_b: z.number().int().nullable(),
  events_a: z.number().int().nullable(),
  n_a_total: z.number().int().nullable(),
  events_b: z.number().int().nullable(),
  n_b_total: z.number().int().nullable(),
  log_hr: z.number().nullable(),
  se_log_hr: z.number().nullable(),
  hr: z.number().nullable(),
  hr_ci_low: z.number().nullable(),
  hr_ci_high: z.number().nullable(),
  r: z.number().nullable(),
  n_r: z.number().int().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type MetaInputRead = z.infer<typeof MetaInputReadSchema>

export const MetaAnalysisReadSchema = z.object({
  id: z.string(),
  review_id: z.string(),
  title: z.string().nullable(),
  effect_metric: EffectMetricSchema,
  model: PoolingModelSchema,
  subgroup_variable: z.string().nullable(),
  pooled_estimate: z.number().nullable(),
  pooled_se: z.number().nullable(),
  ci_low: z.number().nullable(),
  ci_high: z.number().nullable(),
  z_value: z.number().nullable(),
  p_value: z.number().nullable(),
  q_value: z.number().nullable(),
  q_df: z.number().int().nullable(),
  q_p: z.number().nullable(),
  i2: z.number().nullable(),
  tau2: z.number().nullable(),
  subgroup_summary: z.record(z.string(), z.any()).nullable(),
  ai_interpretation: z.string().nullable(),
  status: MetaStatusSchema,
  inputs: z.array(MetaInputReadSchema),
  created_at: z.string(),
  updated_at: z.string(),
})
export type MetaAnalysisRead = z.infer<typeof MetaAnalysisReadSchema>

export type MetaInputCreate = {
  article_id: string
  study_label?: string | null
  mean_a?: number | null
  sd_a?: number | null
  n_a?: number | null
  mean_b?: number | null
  sd_b?: number | null
  n_b?: number | null
  events_a?: number | null
  n_a_total?: number | null
  events_b?: number | null
  n_b_total?: number | null
  log_hr?: number | null
  se_log_hr?: number | null
  hr?: number | null
  hr_ci_low?: number | null
  hr_ci_high?: number | null
  r?: number | null
  n_r?: number | null
}

export type MetaInputUpdate = Omit<MetaInputCreate, 'article_id'>

export type MetaAnalysisCreate = {
  title?: string | null
  effect_metric: EffectMetric
  model: PoolingModel
  subgroup_variable?: string | null
  inputs: MetaInputCreate[]
}

export type MetaAnalysisUpdate = {
  title?: string | null
  effect_metric?: EffectMetric
  model?: PoolingModel
  subgroup_variable?: string | null
}

const API_BASE_URL = API_URL

export const metaAnalysisApi = {
  list: async (projectId: string): Promise<MetaAnalysisRead[]> => {
    const r = await api.get(`/api/projects/${projectId}/reviews/meta`)
    return z.array(MetaAnalysisReadSchema).parse(r.data)
  },
  get: async (projectId: string, metaId: string): Promise<MetaAnalysisRead> => {
    const r = await api.get(`/api/projects/${projectId}/reviews/meta/${metaId}`)
    return MetaAnalysisReadSchema.parse(r.data)
  },
  create: async (
    projectId: string,
    body: MetaAnalysisCreate,
  ): Promise<MetaAnalysisRead> => {
    const r = await api.post(`/api/projects/${projectId}/reviews/meta`, body)
    return MetaAnalysisReadSchema.parse(r.data)
  },
  patch: async (
    projectId: string,
    metaId: string,
    body: MetaAnalysisUpdate,
  ): Promise<MetaAnalysisRead> => {
    const r = await api.patch(
      `/api/projects/${projectId}/reviews/meta/${metaId}`,
      body,
    )
    return MetaAnalysisReadSchema.parse(r.data)
  },
  remove: async (projectId: string, metaId: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/reviews/meta/${metaId}`)
  },
  run: async (projectId: string, metaId: string): Promise<MetaAnalysisRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/reviews/meta/${metaId}/run`,
      {},
      { timeout: 60_000 },
    )
    return MetaAnalysisReadSchema.parse(r.data)
  },
  interpret: async (
    projectId: string,
    metaId: string,
  ): Promise<MetaAnalysisRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/reviews/meta/${metaId}/interpret`,
      {},
      { timeout: 60_000 },
    )
    return MetaAnalysisReadSchema.parse(r.data)
  },
  push: async (
    projectId: string,
    metaId: string,
  ): Promise<ManuscriptSection> => {
    const r = await api.post(
      `/api/projects/${projectId}/reviews/meta/${metaId}/push`,
      {},
    )
    return ManuscriptSectionSchema.parse(r.data)
  },
  forestUrl: (projectId: string, metaId: string): string =>
    `${API_BASE_URL}/api/projects/${projectId}/reviews/meta/${metaId}/forest.png`,
  funnelUrl: (projectId: string, metaId: string): string =>
    `${API_BASE_URL}/api/projects/${projectId}/reviews/meta/${metaId}/funnel.png`,
  upsertInput: async (
    projectId: string,
    metaId: string,
    body: MetaInputCreate,
  ): Promise<MetaInputRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/reviews/meta/${metaId}/inputs`,
      body,
    )
    return MetaInputReadSchema.parse(r.data)
  },
  updateInput: async (
    projectId: string,
    metaId: string,
    inputId: string,
    body: MetaInputUpdate,
  ): Promise<MetaInputRead> => {
    const r = await api.patch(
      `/api/projects/${projectId}/reviews/meta/${metaId}/inputs/${inputId}`,
      body,
    )
    return MetaInputReadSchema.parse(r.data)
  },
  removeInput: async (
    projectId: string,
    metaId: string,
    inputId: string,
  ): Promise<void> => {
    await api.delete(
      `/api/projects/${projectId}/reviews/meta/${metaId}/inputs/${inputId}`,
    )
  },
}

// --- Ingest (Phase 8.6) ---

export const ArticleMetadataSchema = z.object({
  title: z.string(),
  authors: z.array(z.string()).default([]),
  journal: z.string().nullable().optional(),
  year: z.number().int().nullable().optional(),
  volume: z.string().nullable().optional(),
  issue: z.string().nullable().optional(),
  pages: z.string().nullable().optional(),
  doi: z.string().nullable().optional(),
  pmid: z.string().nullable().optional(),
  abstract: z.string().nullable().optional(),
  source: ArticleSourceSchema,
  mesh_terms: z.array(z.string()).default([]),
  affiliations: z.array(z.string()).default([]),
  article_types: z.array(z.string()).default([]),
})
export type ArticleMetadata = z.infer<typeof ArticleMetadataSchema>

export type PubMedSearchFilters = {
  date_from?: string | null
  date_to?: string | null
  article_types?: string[]
  english_only?: boolean
}

export const DuplicateReasonSchema = z.enum([
  'doi_exact',
  'pmid_exact',
  'title_fuzzy',
])
export type DuplicateReason = z.infer<typeof DuplicateReasonSchema>

export const DuplicateGroupSchema = z.object({
  keep_candidate_id: z.string(),
  candidate_ids: z.array(z.string()).min(2),
  reason: DuplicateReasonSchema,
  score: z.number().min(0).max(1),
})
export type DuplicateGroup = z.infer<typeof DuplicateGroupSchema>

export const ImportFromMetadataResponseSchema = z.object({
  created: z.array(ArticleSchema),
  skipped_duplicates: z.array(ArticleSchema),
  duplicate_groups: z.array(DuplicateGroupSchema),
})
export type ImportFromMetadataResponse = z.infer<
  typeof ImportFromMetadataResponseSchema
>

export const ingestApi = {
  lookupDoi: async (
    projectId: string,
    doi: string,
  ): Promise<ArticleMetadata> => {
    const r = await api.post(
      `/api/projects/${projectId}/articles/lookup-doi`,
      { doi },
    )
    return ArticleMetadataSchema.parse(r.data)
  },
  searchPubMed: async (
    projectId: string,
    query: string,
    retmax = 50,
    options?: {
      sort?: 'relevance' | 'date'
      filters?: PubMedSearchFilters
    },
  ): Promise<ArticleMetadata[]> => {
    const body: Record<string, unknown> = { query, retmax }
    if (options?.sort) body.sort = options.sort
    if (options?.filters) body.filters = options.filters
    const r = await api.post(
      `/api/projects/${projectId}/articles/search-pubmed`,
      body,
      { timeout: 30_000 },
    )
    return z.array(ArticleMetadataSchema).parse(r.data)
  },
  importFromMetadata: async (
    projectId: string,
    items: ArticleMetadata[],
  ): Promise<ImportFromMetadataResponse> => {
    const r = await api.post(
      `/api/projects/${projectId}/articles/import-from-metadata`,
      { items },
    )
    return ImportFromMetadataResponseSchema.parse(r.data)
  },
  importRis: async (
    projectId: string,
    file: File,
  ): Promise<ArticleMetadata[]> => {
    const fd = new FormData()
    fd.append('file', file)
    // No explicit Content-Type — see articlesApi.upload for the rationale.
    const r = await api.post(
      `/api/projects/${projectId}/articles/import-ris`,
      fd,
    )
    return z.array(ArticleMetadataSchema).parse(r.data)
  },
  importBibtex: async (
    projectId: string,
    file: File,
  ): Promise<ArticleMetadata[]> => {
    const fd = new FormData()
    fd.append('file', file)
    // No explicit Content-Type — see articlesApi.upload for the rationale.
    const r = await api.post(
      `/api/projects/${projectId}/articles/import-bibtex`,
      fd,
    )
    return z.array(ArticleMetadataSchema).parse(r.data)
  },
  duplicates: async (projectId: string): Promise<DuplicateGroup[]> => {
    const r = await api.get(`/api/projects/${projectId}/articles/duplicates`)
    return z.array(DuplicateGroupSchema).parse(r.data)
  },
  merge: async (
    projectId: string,
    keepId: string,
    dropIds: string[],
  ): Promise<Article> => {
    const r = await api.post(
      `/api/projects/${projectId}/articles/merge-duplicates`,
      { keep_id: keepId, drop_ids: dropIds },
    )
    return ArticleSchema.parse(r.data)
  },
}

// exposed for tests
export const __internal = {
  parseContentDispositionFilename,
  triggerBlobDownload,
  extractErrorMessage,
}


// ──────────────────────────────────────────────────────────────────────
// Phase 8.7 — Figures, CONSORT, Journal templates
// ──────────────────────────────────────────────────────────────────────

export const ImageMimeSchema = z.enum(['image/png', 'image/jpeg', 'image/svg+xml'])
export type ImageMime = z.infer<typeof ImageMimeSchema>

export const FigureSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  figure_number: z.number().int(),
  caption: z.string(),
  alt_text: z.string(),
  file_type: ImageMimeSchema,
  width_px: z.number().int().nullable(),
  height_px: z.number().int().nullable(),
  byte_size: z.number().int(),
  file_url: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type Figure = z.infer<typeof FigureSchema>

export const figuresApi = {
  list: async (projectId: string): Promise<Figure[]> => {
    const r = await api.get(`/api/projects/${projectId}/figures`)
    return z.array(FigureSchema).parse(r.data)
  },
  upload: async (projectId: string, file: File): Promise<Figure> => {
    const fd = new FormData()
    fd.append('file', file)
    const r = await api.post(`/api/projects/${projectId}/figures`, fd)
    return FigureSchema.parse(r.data)
  },
  get: async (figureId: string): Promise<Figure> => {
    const r = await api.get(`/api/figures/${figureId}`)
    return FigureSchema.parse(r.data)
  },
  patch: async (
    figureId: string,
    body: { caption?: string; alt_text?: string },
  ): Promise<Figure> => {
    const r = await api.patch(`/api/figures/${figureId}`, body)
    return FigureSchema.parse(r.data)
  },
  reorder: async (projectId: string, orderedIds: string[]): Promise<Figure[]> => {
    const r = await api.post(
      `/api/projects/${projectId}/figures/reorder`,
      { ordered_figure_ids: orderedIds },
    )
    return z.array(FigureSchema).parse(r.data)
  },
  remove: async (figureId: string): Promise<void> => {
    await api.delete(`/api/figures/${figureId}`)
  },
}

export const ConsortDataSchema = z.object({
  enrollment_assessed: z.number().int().nullable().optional(),
  enrollment_excluded: z.number().int().nullable().optional(),
  enrollment_excluded_reasons: z.record(z.string(), z.number().int()).nullable().optional(),
  randomised: z.number().int().nullable().optional(),
  allocated_intervention: z.number().int().nullable().optional(),
  allocated_control: z.number().int().nullable().optional(),
  intervention_received: z.number().int().nullable().optional(),
  control_received: z.number().int().nullable().optional(),
  intervention_lost_followup: z.number().int().nullable().optional(),
  control_lost_followup: z.number().int().nullable().optional(),
  intervention_discontinued: z.number().int().nullable().optional(),
  control_discontinued: z.number().int().nullable().optional(),
  intervention_analysed: z.number().int().nullable().optional(),
  control_analysed: z.number().int().nullable().optional(),
})
export type ConsortDataPayload = z.infer<typeof ConsortDataSchema>

export const ConsortReadSchema = ConsortDataSchema.extend({
  id: z.string(),
  project_id: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type ConsortRead = z.infer<typeof ConsortReadSchema>

export const ConsortGetResponseSchema = z.object({
  data: ConsortReadSchema,
  warnings: z.array(z.string()),
  svg_base64: z.string(),
})
export type ConsortGetResponse = z.infer<typeof ConsortGetResponseSchema>

export const consortApi = {
  get: async (projectId: string): Promise<ConsortGetResponse> => {
    const r = await api.get(`/api/projects/${projectId}/consort`)
    return ConsortGetResponseSchema.parse(r.data)
  },
  patch: async (projectId: string, body: ConsortDataPayload): Promise<ConsortGetResponse> => {
    const r = await api.patch(`/api/projects/${projectId}/consort`, body)
    return ConsortGetResponseSchema.parse(r.data)
  },
  push: async (projectId: string): Promise<ManuscriptSection> => {
    const r = await api.post(`/api/projects/${projectId}/consort/push`)
    return ManuscriptSectionSchema.parse(r.data)
  },
}

export const JournalTemplateSchema = z.object({
  key: z.string(),
  label: z.string(),
  max_total_words: z.number().int(),
  max_words_by_section: z.record(z.string(), z.number().int()),
  required_sections: z.array(z.string()),
  structured_abstract: z.boolean(),
  reference_style: z.enum(['vancouver', 'apa', 'harvard']),
  max_figures: z.number().int().nullable().optional(),
  max_tables: z.number().int().nullable().optional(),
})
export type JournalTemplate = z.infer<typeof JournalTemplateSchema>

export const journalTemplatesApi = {
  list: async (): Promise<JournalTemplate[]> => {
    const r = await api.get('/api/journal-templates')
    return z.array(JournalTemplateSchema).parse(r.data)
  },
}

// ── Phase 10: ICMJE structured front-matter ──────────────────────────────

export const CreditRoleSchema = z.enum([
  'Conceptualization',
  'Data curation',
  'Formal analysis',
  'Funding acquisition',
  'Investigation',
  'Methodology',
  'Project administration',
  'Resources',
  'Software',
  'Supervision',
  'Validation',
  'Visualization',
  'Writing – original draft',
  'Writing – review & editing',
])
export type CreditRole = z.infer<typeof CreditRoleSchema>
export const CREDIT_ROLES: readonly CreditRole[] = CreditRoleSchema.options

export const AuthorReadSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  full_name: z.string(),
  given_name: z.string(),
  family_name: z.string(),
  orcid: z.string().nullable(),
  email: z.string().nullable(),
  is_corresponding: z.boolean(),
  position: z.number().int(),
  created_at: z.string(),
  updated_at: z.string(),
  affiliation_ids: z.array(z.string()),
})
export type AuthorRead = z.infer<typeof AuthorReadSchema>

export const AuthorCreateSchema = z.object({
  full_name: z.string().min(1),
  given_name: z.string().optional(),
  family_name: z.string().optional(),
  orcid: z.string().nullable().optional(),
  email: z.string().nullable().optional(),
  is_corresponding: z.boolean().optional(),
})
export type AuthorCreate = z.infer<typeof AuthorCreateSchema>

export type AuthorUpdate = Partial<AuthorCreate>

export const AffiliationReadSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  name: z.string(),
  address: z.string().nullable(),
  city: z.string().nullable(),
  country: z.string().nullable(),
  position: z.number().int(),
  created_at: z.string(),
})
export type AffiliationRead = z.infer<typeof AffiliationReadSchema>

export const AffiliationCreateSchema = z.object({
  name: z.string().min(1),
  address: z.string().nullable().optional(),
  city: z.string().nullable().optional(),
  country: z.string().nullable().optional(),
})
export type AffiliationCreate = z.infer<typeof AffiliationCreateSchema>
export type AffiliationUpdate = Partial<AffiliationCreate>

export const ContributionReadSchema = z.object({
  id: z.string(),
  author_id: z.string(),
  role: CreditRoleSchema,
})
export type ContributionRead = z.infer<typeof ContributionReadSchema>

export const FunderSchema = z.object({
  name: z.string().min(1),
  grant_id: z.string().nullable().optional(),
})
export type Funder = z.infer<typeof FunderSchema>

export const StructuredAbstractSchema = z.object({
  background: z.string(),
  methods: z.string(),
  results: z.string(),
  conclusions: z.string(),
})
export type StructuredAbstractValue = z.infer<typeof StructuredAbstractSchema>

export const ProjectFrontmatterSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  funding_statement: z.string().nullable(),
  funders: z.array(FunderSchema),
  ethics_irb: z.string().nullable(),
  ethics_approval_number: z.string().nullable(),
  ethics_consent: z.string().nullable(),
  conflicts_statement: z.string().nullable(),
  structured_abstract_enabled: z.boolean(),
  structured_abstract: StructuredAbstractSchema,
  updated_at: z.string(),
})
export type ProjectFrontmatter = z.infer<typeof ProjectFrontmatterSchema>

export type ProjectFrontmatterUpdate = {
  funding_statement?: string | null
  funders?: Funder[]
  ethics_irb?: string | null
  ethics_approval_number?: string | null
  ethics_consent?: string | null
  conflicts_statement?: string | null
  structured_abstract_enabled?: boolean
  structured_abstract?: StructuredAbstractValue
}

export const frontmatterApi = {
  authors: {
    list: async (projectId: string): Promise<AuthorRead[]> => {
      const r = await api.get(`/api/projects/${projectId}/authors`)
      return z.array(AuthorReadSchema).parse(r.data)
    },
    create: async (projectId: string, body: AuthorCreate): Promise<AuthorRead> => {
      const r = await api.post(`/api/projects/${projectId}/authors`, body)
      return AuthorReadSchema.parse(r.data)
    },
    update: async (authorId: string, patch: AuthorUpdate): Promise<AuthorRead> => {
      const r = await api.patch(`/api/authors/${authorId}`, patch)
      return AuthorReadSchema.parse(r.data)
    },
    delete: async (authorId: string): Promise<void> => {
      await api.delete(`/api/authors/${authorId}`)
    },
    reorder: async (projectId: string, orderedIds: string[]): Promise<AuthorRead[]> => {
      const r = await api.post(`/api/projects/${projectId}/authors/reorder`, {
        ordered_author_ids: orderedIds,
      })
      return z.array(AuthorReadSchema).parse(r.data)
    },
    setCorresponding: async (authorId: string): Promise<AuthorRead> => {
      const r = await api.post(`/api/authors/${authorId}/set-corresponding`)
      return AuthorReadSchema.parse(r.data)
    },
  },
  affiliations: {
    list: async (projectId: string): Promise<AffiliationRead[]> => {
      const r = await api.get(`/api/projects/${projectId}/affiliations`)
      return z.array(AffiliationReadSchema).parse(r.data)
    },
    create: async (
      projectId: string,
      body: AffiliationCreate,
    ): Promise<AffiliationRead> => {
      const r = await api.post(`/api/projects/${projectId}/affiliations`, body)
      return AffiliationReadSchema.parse(r.data)
    },
    update: async (
      affiliationId: string,
      patch: AffiliationUpdate,
    ): Promise<AffiliationRead> => {
      const r = await api.patch(`/api/affiliations/${affiliationId}`, patch)
      return AffiliationReadSchema.parse(r.data)
    },
    delete: async (affiliationId: string): Promise<void> => {
      await api.delete(`/api/affiliations/${affiliationId}`)
    },
    reorder: async (
      projectId: string,
      orderedIds: string[],
    ): Promise<AffiliationRead[]> => {
      const r = await api.post(`/api/projects/${projectId}/affiliations/reorder`, {
        ordered_affiliation_ids: orderedIds,
      })
      return z.array(AffiliationReadSchema).parse(r.data)
    },
  },
  link: {
    add: async (authorId: string, affiliationId: string): Promise<AuthorRead> => {
      const r = await api.post(
        `/api/authors/${authorId}/affiliations/${affiliationId}`,
      )
      return AuthorReadSchema.parse(r.data)
    },
    remove: async (
      authorId: string,
      affiliationId: string,
    ): Promise<AuthorRead> => {
      const r = await api.delete(
        `/api/authors/${authorId}/affiliations/${affiliationId}`,
      )
      return AuthorReadSchema.parse(r.data)
    },
  },
  contributions: {
    list: async (authorId: string): Promise<ContributionRead[]> => {
      const r = await api.get(`/api/authors/${authorId}/contributions`)
      return z.array(ContributionReadSchema).parse(r.data)
    },
    set: async (authorId: string, role: CreditRole): Promise<ContributionRead> => {
      const r = await api.post(`/api/authors/${authorId}/contributions`, { role })
      return ContributionReadSchema.parse(r.data)
    },
    clear: async (authorId: string, role: CreditRole): Promise<void> => {
      await api.delete(
        `/api/authors/${authorId}/contributions/${encodeURIComponent(role)}`,
      )
    },
  },
  frontmatter: {
    get: async (projectId: string): Promise<ProjectFrontmatter> => {
      const r = await api.get(`/api/projects/${projectId}/frontmatter`)
      return ProjectFrontmatterSchema.parse(r.data)
    },
    patch: async (
      projectId: string,
      body: ProjectFrontmatterUpdate,
    ): Promise<ProjectFrontmatter> => {
      const r = await api.patch(`/api/projects/${projectId}/frontmatter`, body)
      return ProjectFrontmatterSchema.parse(r.data)
    },
  },
}

// ── Phase 11: Manuscript snapshots ────────────────────────────────────

export const SnapshotSummarySchema = z.object({
  id: z.string(),
  project_id: z.string(),
  label: z.string(),
  description: z.string().nullable(),
  created_at: z.string(),
})
export type SnapshotSummary = z.infer<typeof SnapshotSummarySchema>

export const SnapshotReadSchema = SnapshotSummarySchema.extend({
  full_blob: z.record(z.any()),
})
export type SnapshotRead = z.infer<typeof SnapshotReadSchema>

export const DiffLineSchema = z.object({
  type: z.string(),
  line: z.string(),
})
export type DiffLine = z.infer<typeof DiffLineSchema>

export const SnapshotDiffResponseSchema = z.object({
  base_snapshot_id: z.string(),
  target_snapshot_id: z.string().nullable(),
  sections: z.record(z.array(DiffLineSchema)),
})
export type SnapshotDiffResponse = z.infer<typeof SnapshotDiffResponseSchema>

export type SnapshotCreate = {
  label: string
  description?: string | null
}

export const snapshotsApi = {
  list: async (projectId: string): Promise<SnapshotSummary[]> => {
    const r = await api.get(`/api/projects/${projectId}/snapshots`)
    return z.array(SnapshotSummarySchema).parse(r.data)
  },
  create: async (projectId: string, body: SnapshotCreate): Promise<SnapshotRead> => {
    const r = await api.post(`/api/projects/${projectId}/snapshots`, body)
    return SnapshotReadSchema.parse(r.data)
  },
  get: async (projectId: string, snapshotId: string): Promise<SnapshotRead> => {
    const r = await api.get(`/api/projects/${projectId}/snapshots/${snapshotId}`)
    return SnapshotReadSchema.parse(r.data)
  },
  diff: async (
    projectId: string,
    snapshotId: string,
    targetId?: string,
  ): Promise<SnapshotDiffResponse> => {
    const params = targetId ? { target: targetId } : undefined
    const r = await api.get(
      `/api/projects/${projectId}/snapshots/${snapshotId}/diff`,
      { params },
    )
    return SnapshotDiffResponseSchema.parse(r.data)
  },
  delete: async (projectId: string, snapshotId: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/snapshots/${snapshotId}`)
  },
}

// ── Phase 11: Margin comments ─────────────────────────────────────────

export const CommentSectionSchema = z.enum([
  'Abstract',
  'Introduction',
  'Methodology',
  'Results',
  'Discussion',
  'Conclusion',
  'FrontMatter',
])
export type CommentSection = z.infer<typeof CommentSectionSchema>

export const CommentReadSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  section_name: z.string(),
  anchor_start: z.number().int(),
  anchor_end: z.number().int(),
  body: z.string(),
  resolved: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type CommentRead = z.infer<typeof CommentReadSchema>

export type CommentCreate = {
  section_name: CommentSection
  anchor_start: number
  anchor_end: number
  body: string
}

export type CommentUpdate = {
  body?: string
  resolved?: boolean
}

export const commentsApi = {
  list: async (
    projectId: string,
    filters?: { section?: CommentSection; resolved?: boolean },
  ): Promise<CommentRead[]> => {
    const params: Record<string, string | boolean> = {}
    if (filters?.section) params.section = filters.section
    if (filters?.resolved !== undefined) params.resolved = filters.resolved
    const r = await api.get(`/api/projects/${projectId}/comments`, { params })
    return z.array(CommentReadSchema).parse(r.data)
  },
  create: async (projectId: string, body: CommentCreate): Promise<CommentRead> => {
    const r = await api.post(`/api/projects/${projectId}/comments`, body)
    return CommentReadSchema.parse(r.data)
  },
  update: async (
    projectId: string,
    commentId: string,
    body: CommentUpdate,
  ): Promise<CommentRead> => {
    const r = await api.patch(
      `/api/projects/${projectId}/comments/${commentId}`,
      body,
    )
    return CommentReadSchema.parse(r.data)
  },
  delete: async (projectId: string, commentId: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/comments/${commentId}`)
  },
}

// ── Phase 12: Cover letter ─────────────────────────────────────────────

export const CoverLetterReadSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  target_journal: z.string().nullable(),
  novelty_points: z.array(z.string()),
  body_html: z.string(),
  ai_model: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type CoverLetterRead = z.infer<typeof CoverLetterReadSchema>

export type CoverLetterUpdate = {
  target_journal?: string | null
  novelty_points?: string[]
  body_html?: string
}

export type CoverLetterDraftRequest = {
  target_journal?: string | null
  novelty_points?: string[]
}

export const coverLetterApi = {
  get: async (projectId: string): Promise<CoverLetterRead> => {
    const r = await api.get(`/api/projects/${projectId}/cover-letter`)
    return CoverLetterReadSchema.parse(r.data)
  },
  update: async (
    projectId: string,
    body: CoverLetterUpdate,
  ): Promise<CoverLetterRead> => {
    const r = await api.patch(`/api/projects/${projectId}/cover-letter`, body)
    return CoverLetterReadSchema.parse(r.data)
  },
  draft: async (
    projectId: string,
    body: CoverLetterDraftRequest = {},
  ): Promise<CoverLetterRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/cover-letter/draft`,
      body,
    )
    return CoverLetterReadSchema.parse(r.data)
  },
}

// ── Phase 12: Reviewer responses ───────────────────────────────────────

export const CommentResponseSchema = z.object({
  comment_text: z.string(),
  response_html: z.string(),
})
export type CommentResponse = z.infer<typeof CommentResponseSchema>

export const ReviewerResponseReadSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  reviewer_label: z.string(),
  comments: z.array(CommentResponseSchema),
  created_at: z.string(),
  updated_at: z.string(),
})
export type ReviewerResponseRead = z.infer<typeof ReviewerResponseReadSchema>

export type ReviewerResponseCreate = {
  reviewer_label: string
  raw_comments: string
}

export type ReviewerResponseUpdate = {
  reviewer_label?: string
  comments?: CommentResponse[]
}

export const reviewerResponseApi = {
  list: async (projectId: string): Promise<ReviewerResponseRead[]> => {
    const r = await api.get(`/api/projects/${projectId}/reviewer-responses`)
    return z.array(ReviewerResponseReadSchema).parse(r.data)
  },
  create: async (
    projectId: string,
    body: ReviewerResponseCreate,
  ): Promise<ReviewerResponseRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/reviewer-responses`,
      body,
    )
    return ReviewerResponseReadSchema.parse(r.data)
  },
  update: async (
    projectId: string,
    responseId: string,
    body: ReviewerResponseUpdate,
  ): Promise<ReviewerResponseRead> => {
    const r = await api.patch(
      `/api/projects/${projectId}/reviewer-responses/${responseId}`,
      body,
    )
    return ReviewerResponseReadSchema.parse(r.data)
  },
  delete: async (projectId: string, responseId: string): Promise<void> => {
    await api.delete(
      `/api/projects/${projectId}/reviewer-responses/${responseId}`,
    )
  },
}

// ── Phase 13 (MP13): Dataset transformations ───────────────────────────

export const TransformationOpTypeSchema = z.enum([
  'filter',
  'mutate',
  'select',
  'recode',
  'drop_na',
  'log_transform',
  'z_score',
  'group_summarise',
])
export type TransformationOpType = z.infer<typeof TransformationOpTypeSchema>

export const TransformationReadSchema = z.object({
  id: z.string(),
  dataset_id: z.string(),
  position: z.number().int(),
  op_type: TransformationOpTypeSchema,
  op_args: z.record(z.string(), z.any()),
  label: z.string(),
  created_at: z.string(),
})
export type TransformationRead = z.infer<typeof TransformationReadSchema>

export type TransformationCreate = {
  op_type: TransformationOpType
  op_args?: Record<string, unknown>
  label?: string
  position?: number | null
}

export type TransformationUpdate = {
  op_args?: Record<string, unknown>
  label?: string
  position?: number
}

export const transformationsApi = {
  list: async (
    projectId: string,
    datasetId: string,
  ): Promise<TransformationRead[]> => {
    const r = await api.get(
      `/api/projects/${projectId}/datasets/${datasetId}/transformations`,
    )
    return z.array(TransformationReadSchema).parse(r.data)
  },
  add: async (
    projectId: string,
    datasetId: string,
    body: TransformationCreate,
  ): Promise<TransformationRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/transformations`,
      body,
    )
    return TransformationReadSchema.parse(r.data)
  },
  update: async (
    projectId: string,
    datasetId: string,
    transformationId: string,
    body: TransformationUpdate,
  ): Promise<TransformationRead> => {
    const r = await api.patch(
      `/api/projects/${projectId}/datasets/${datasetId}/transformations/${transformationId}`,
      body,
    )
    return TransformationReadSchema.parse(r.data)
  },
  delete: async (
    projectId: string,
    datasetId: string,
    transformationId: string,
  ): Promise<void> => {
    await api.delete(
      `/api/projects/${projectId}/datasets/${datasetId}/transformations/${transformationId}`,
    )
  },
  reorder: async (
    projectId: string,
    datasetId: string,
    ids: string[],
  ): Promise<TransformationRead[]> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/transformations/reorder`,
      { ids },
    )
    return z.array(TransformationReadSchema).parse(r.data)
  },
}

// ── Phase 13 (MP13): Cross-dataset op ──────────────────────────────────

export const CrossOpNameSchema = z.enum(['merge', 'append', 'join'])
export type CrossOpName = z.infer<typeof CrossOpNameSchema>

export const CrossOpResponseSchema = z.object({
  dataset_id: z.string(),
  filename: z.string(),
  n_rows: z.number().int(),
  n_columns: z.number().int(),
  source_dataset_ids: z.array(z.string()),
})
export type CrossOpResponse = z.infer<typeof CrossOpResponseSchema>

export type CrossOpRequest = {
  op: CrossOpName
  source_dataset_ids: string[]
  args?: Record<string, unknown>
  filename?: string
}

export const crossDatasetApi = {
  crossOp: async (
    projectId: string,
    body: CrossOpRequest,
  ): Promise<CrossOpResponse> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/cross-op`,
      body,
    )
    return CrossOpResponseSchema.parse(r.data)
  },
}

// ── Phase 13 (MP13): Power calculator ──────────────────────────────────

export const PowerTestFamilySchema = z.enum([
  'ttest_ind',
  'ttest_paired',
  'anova',
  'chi_square',
  'correlation',
  // Phase 17 (MP17) extras — also exposed by the FE Power calculator.
  'logrank',
  'mixed_effects',
  'noninferiority',
])
export type PowerTestFamily = z.infer<typeof PowerTestFamilySchema>

export const POWER_FAMILY_LABELS: Record<PowerTestFamily, string> = {
  ttest_ind: 'Independent t-test',
  ttest_paired: 'Paired t-test',
  anova: 'One-way ANOVA',
  chi_square: 'Chi-square',
  correlation: 'Correlation',
  logrank: 'Survival (log-rank)',
  mixed_effects: 'Cluster RCT (mixed-effects)',
  noninferiority: 'Non-inferiority',
}

export const PowerResponseSchema = z.object({
  required_n: z.number().int(),
  required_n_per_group: z.number().int().nullable(),
  alpha: z.number(),
  power: z.number(),
  effect_size: z.number(),
  sensitivity_curve_png: z.string(),
  notes: z.string(),
  required_events: z.number().int().nullable().optional(),
  required_clusters_per_arm: z.number().int().nullable().optional(),
  design_effect: z.number().nullable().optional(),
})
export type PowerResponse = z.infer<typeof PowerResponseSchema>

export type PowerRequest = {
  test_family: PowerTestFamily
  effect_size: number
  alpha?: number
  power?: number
  k_groups?: number | null
  df?: number | null
  event_rate?: number | null
  allocation_ratio?: number | null
  n_per_cluster?: number | null
  n_clusters?: number | null
  icc?: number | null
  sigma?: number | null
}

export const powerApi = {
  calculate: async (body: PowerRequest): Promise<PowerResponse> => {
    const r = await api.post('/api/power', body)
    return PowerResponseSchema.parse(r.data)
  },
}

// ── Phase 13 (MP13): Propensity Score Matching ─────────────────────────

export const CovariateBalanceRowSchema = z.object({
  covariate: z.string(),
  smd: z.number(),
  mean_treated: z.number(),
  mean_control: z.number(),
})
export type CovariateBalanceRow = z.infer<typeof CovariateBalanceRowSchema>

export const PSMResponseSchema = z.object({
  matched_dataset_id: z.string(),
  n_treated_total: z.number().int(),
  n_control_total: z.number().int(),
  n_treated_matched: z.number().int(),
  n_control_matched: z.number().int(),
  caliper_sd: z.number(),
  balance_before: z.array(CovariateBalanceRowSchema),
  balance_after: z.array(CovariateBalanceRowSchema),
  max_smd_before: z.number(),
  max_smd_after: z.number(),
})
export type PSMResponse = z.infer<typeof PSMResponseSchema>

export type PSMRequest = {
  treatment_col: string
  covariate_cols: string[]
  caliper_sd?: number
}

export const psmApi = {
  run: async (
    projectId: string,
    datasetId: string,
    body: PSMRequest,
  ): Promise<PSMResponse> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/psm`,
      body,
      { timeout: 60_000 },
    )
    return PSMResponseSchema.parse(r.data)
  },
}

// ── Phase 13.5 (MP13.5): Dataset plots ────────────────────────────────

export const PlotGeomSchema = z.enum([
  'point',
  'bar',
  'line',
  'box',
  'violin',
  'heatmap',
  'histogram',
  'density',
  'pair',
])
export type PlotGeom = z.infer<typeof PlotGeomSchema>

export const PlotSpecSchema = z.object({
  geom: PlotGeomSchema,
  x: z.string().nullable().optional(),
  y: z.string().nullable().optional(),
  color: z.string().nullable().optional(),
  facet: z.string().nullable().optional(),
  args: z.record(z.string(), z.unknown()).optional(),
})
export type PlotSpec = z.infer<typeof PlotSpecSchema>

export const PlotReadSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  dataset_id: z.string(),
  title: z.string(),
  spec: z.record(z.string(), z.unknown()),
  png_data_uri: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type PlotRead = z.infer<typeof PlotReadSchema>

export type PlotCreate = {
  geom: PlotGeom
  x?: string | null
  y?: string | null
  color?: string | null
  facet?: string | null
  args?: Record<string, unknown>
  title?: string
}

export const plotsApi = {
  list: async (projectId: string, datasetId: string): Promise<PlotRead[]> => {
    const r = await api.get(
      `/api/projects/${projectId}/datasets/${datasetId}/plots`,
    )
    return z.array(PlotReadSchema).parse(r.data)
  },
  create: async (
    projectId: string,
    datasetId: string,
    body: PlotCreate,
  ): Promise<PlotRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/plots`,
      body,
      { timeout: 60_000 },
    )
    return PlotReadSchema.parse(r.data)
  },
  delete: async (projectId: string, plotId: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/plots/${plotId}`)
  },
  regenerate: async (
    projectId: string,
    plotId: string,
  ): Promise<PlotRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/plots/${plotId}/regenerate`,
      {},
      { timeout: 60_000 },
    )
    return PlotReadSchema.parse(r.data)
  },
}

// ── Phase 13.5 (MP13.5): Analysis plans + runs ─────────────────────────

export const PlanStepTypeSchema = z.enum(['transform', 'test', 'plot'])
export type PlanStepType = z.infer<typeof PlanStepTypeSchema>

export const PlanStepSchema = z.object({
  type: PlanStepTypeSchema,
  args: z.record(z.string(), z.unknown()).default({}),
})
export type PlanStep = z.infer<typeof PlanStepSchema>

export const AnalysisPlanReadSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  name: z.string(),
  description: z.string().nullable(),
  steps: z.array(z.record(z.string(), z.unknown())),
  created_at: z.string(),
  updated_at: z.string(),
})
export type AnalysisPlanRead = z.infer<typeof AnalysisPlanReadSchema>

export type AnalysisPlanCreate = {
  name: string
  description?: string | null
  steps: PlanStep[]
}
export type AnalysisPlanUpdate = Partial<AnalysisPlanCreate>

export const PlanRunStatusSchema = z.enum(['ok', 'partial', 'failed'])
export type PlanRunStatus = z.infer<typeof PlanRunStatusSchema>

export const AnalysisPlanRunReadSchema = z.object({
  id: z.string(),
  plan_id: z.string(),
  dataset_id: z.string(),
  executed_at: z.string(),
  result_blob: z.record(z.string(), z.unknown()),
  status: PlanRunStatusSchema,
  error: z.string().nullable(),
})
export type AnalysisPlanRunRead = z.infer<typeof AnalysisPlanRunReadSchema>

export const analysisPlansApi = {
  list: async (projectId: string): Promise<AnalysisPlanRead[]> => {
    const r = await api.get(`/api/projects/${projectId}/analysis-plans`)
    return z.array(AnalysisPlanReadSchema).parse(r.data)
  },
  get: async (projectId: string, planId: string): Promise<AnalysisPlanRead> => {
    const r = await api.get(
      `/api/projects/${projectId}/analysis-plans/${planId}`,
    )
    return AnalysisPlanReadSchema.parse(r.data)
  },
  create: async (
    projectId: string,
    body: AnalysisPlanCreate,
  ): Promise<AnalysisPlanRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/analysis-plans`,
      body,
    )
    return AnalysisPlanReadSchema.parse(r.data)
  },
  update: async (
    projectId: string,
    planId: string,
    body: AnalysisPlanUpdate,
  ): Promise<AnalysisPlanRead> => {
    const r = await api.patch(
      `/api/projects/${projectId}/analysis-plans/${planId}`,
      body,
    )
    return AnalysisPlanReadSchema.parse(r.data)
  },
  delete: async (projectId: string, planId: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/analysis-plans/${planId}`)
  },
  run: async (
    projectId: string,
    planId: string,
    datasetId: string,
  ): Promise<AnalysisPlanRunRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/analysis-plans/${planId}/run`,
      { dataset_id: datasetId },
      { timeout: 120_000 },
    )
    return AnalysisPlanRunReadSchema.parse(r.data)
  },
  listRuns: async (
    projectId: string,
    planId: string,
  ): Promise<AnalysisPlanRunRead[]> => {
    const r = await api.get(
      `/api/projects/${projectId}/analysis-plans/${planId}/runs`,
    )
    return z.array(AnalysisPlanRunReadSchema).parse(r.data)
  },
  getRun: async (
    projectId: string,
    runId: string,
  ): Promise<AnalysisPlanRunRead> => {
    const r = await api.get(
      `/api/projects/${projectId}/analysis-plan-runs/${runId}`,
    )
    return AnalysisPlanRunReadSchema.parse(r.data)
  },
}

// ── Phase 13.5 (MP13.5): Statistical report PDF export ────────────────

export const statsReportApi = {
  export: async (projectId: string, datasetId: string): Promise<Blob> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/report`,
      {},
      { responseType: 'blob', timeout: 120_000 },
    )
    return r.data as Blob
  },
}

// ── Phase 14 (MP14): GRADE certainty + Summary-of-Findings ────────────

export const GradeStartingCertaintySchema = z.enum(['high', 'low'])
export type GradeStartingCertainty = z.infer<
  typeof GradeStartingCertaintySchema
>

export const GradeDowngradeLevelSchema = z.enum([
  'not_serious',
  'serious',
  'very_serious',
])
export type GradeDowngradeLevel = z.infer<typeof GradeDowngradeLevelSchema>

export const GradeUpgradeLevelSchema = z.enum(['none', 'present', 'large'])
export type GradeUpgradeLevel = z.infer<typeof GradeUpgradeLevelSchema>

export const GradeSmallUpgradeSchema = z.enum(['none', 'present'])
export type GradeSmallUpgrade = z.infer<typeof GradeSmallUpgradeSchema>

export const GradeCertaintySchema = z.enum([
  'high',
  'moderate',
  'low',
  'very_low',
])
export type GradeCertainty = z.infer<typeof GradeCertaintySchema>

export const GradeAssessmentReadSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  review_id: z.string(),
  meta_id: z.string().nullable(),
  outcome_label: z.string(),
  starting_certainty: GradeStartingCertaintySchema,
  domain_risk_of_bias: GradeDowngradeLevelSchema,
  domain_inconsistency: GradeDowngradeLevelSchema,
  domain_indirectness: GradeDowngradeLevelSchema,
  domain_imprecision: GradeDowngradeLevelSchema,
  domain_publication_bias: GradeDowngradeLevelSchema,
  upgrade_large_effect: GradeUpgradeLevelSchema,
  upgrade_dose_response: GradeSmallUpgradeSchema,
  upgrade_confounders_against: GradeSmallUpgradeSchema,
  certainty: GradeCertaintySchema,
  notes: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type GradeAssessmentRead = z.infer<typeof GradeAssessmentReadSchema>

export type GradeAssessmentCreate = {
  outcome_label: string
  starting_certainty: GradeStartingCertainty
  domain_risk_of_bias: GradeDowngradeLevel
  domain_inconsistency: GradeDowngradeLevel
  domain_indirectness: GradeDowngradeLevel
  domain_imprecision: GradeDowngradeLevel
  domain_publication_bias: GradeDowngradeLevel
  upgrade_large_effect: GradeUpgradeLevel
  upgrade_dose_response: GradeSmallUpgrade
  upgrade_confounders_against: GradeSmallUpgrade
  notes?: string | null
  meta_id?: string | null
}

export const gradeApi = {
  list: async (projectId: string): Promise<GradeAssessmentRead[]> => {
    const r = await api.get(`/api/projects/${projectId}/review/grade`)
    return z.array(GradeAssessmentReadSchema).parse(r.data)
  },
  upsert: async (
    projectId: string,
    body: GradeAssessmentCreate,
  ): Promise<GradeAssessmentRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/review/grade`,
      body,
    )
    return GradeAssessmentReadSchema.parse(r.data)
  },
  remove: async (projectId: string, gradeId: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/review/grade/${gradeId}`)
  },
  push: async (projectId: string): Promise<ManuscriptSection> => {
    const r = await api.post(
      `/api/projects/${projectId}/review/grade/push`,
      {},
    )
    return ManuscriptSectionSchema.parse(r.data)
  },
}

// ── Phase 14 (MP14): PROSPERO registration draft ──────────────────────

export const ProsperoDraftReadSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  review_id: z.string(),
  fields: z.record(z.string(), z.string()),
  updated_at: z.string(),
})
export type ProsperoDraftRead = z.infer<typeof ProsperoDraftReadSchema>

export const PROSPERO_FIELDS: readonly { key: string; label: string }[] = [
  { key: 'title', label: 'Review title' },
  { key: 'anticipated_start_date', label: 'Anticipated or actual start date' },
  { key: 'anticipated_completion_date', label: 'Anticipated completion date' },
  { key: 'stage', label: 'Stage of review at time of this submission' },
  { key: 'named_contact', label: 'Named contact' },
  { key: 'named_contact_email', label: 'Named contact email' },
  { key: 'named_contact_address', label: 'Named contact address' },
  {
    key: 'organisational_affiliation',
    label: 'Organisational affiliation of the review',
  },
  {
    key: 'review_team_members',
    label: 'Review team members and their organisational affiliations',
  },
  { key: 'funding_sources', label: 'Funding sources/sponsors' },
  { key: 'conflicts_of_interest', label: 'Conflicts of interest' },
  { key: 'collaborators', label: 'Collaborators' },
  { key: 'review_question', label: 'Review question' },
  { key: 'searches', label: 'Searches' },
  {
    key: 'url_to_protocol',
    label: 'URL to search strategy / additional protocol',
  },
  { key: 'condition_or_domain', label: 'Condition or domain being studied' },
  { key: 'participants', label: 'Participants/population' },
  { key: 'intervention_exposure', label: 'Intervention(s), exposure(s)' },
  { key: 'comparators_control', label: 'Comparator(s)/control' },
  { key: 'types_of_study', label: 'Types of study to be included' },
  { key: 'context', label: 'Context' },
  { key: 'primary_outcomes', label: 'Main outcome(s)' },
]

export const prosperoApi = {
  get: async (projectId: string): Promise<ProsperoDraftRead> => {
    const r = await api.get(`/api/projects/${projectId}/review/prospero`)
    return ProsperoDraftReadSchema.parse(r.data)
  },
  patch: async (
    projectId: string,
    fields: Record<string, string>,
  ): Promise<ProsperoDraftRead> => {
    const r = await api.patch(
      `/api/projects/${projectId}/review/prospero`,
      { fields },
    )
    return ProsperoDraftReadSchema.parse(r.data)
  },
  export: async (projectId: string): Promise<string> => {
    const r = await api.post(
      `/api/projects/${projectId}/review/prospero/export`,
      undefined,
      { responseType: 'text' },
    )
    return typeof r.data === 'string' ? r.data : String(r.data)
  },
}

// ── Phase 15 (MP15): Living systematic review ─────────────────────────

export const LivingScheduleSchema = z.enum(['daily', 'weekly', 'monthly'])
export type LivingSchedule = z.infer<typeof LivingScheduleSchema>

export const LivingHitDecisionSchema = z.enum(['new', 'dismissed', 'accepted'])
export type LivingHitDecision = z.infer<typeof LivingHitDecisionSchema>

export const LivingReviewJobReadSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  review_id: z.string(),
  pubmed_query: z.string(),
  schedule: LivingScheduleSchema,
  enabled: z.boolean(),
  last_run_at: z.string().nullable(),
  last_hit_count: z.number().int().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type LivingReviewJobRead = z.infer<typeof LivingReviewJobReadSchema>

export const LivingReviewHitReadSchema = z.object({
  id: z.string(),
  job_id: z.string(),
  run_at: z.string(),
  pmid: z.string(),
  title: z.string(),
  decision: LivingHitDecisionSchema,
  seen_in_baseline: z.boolean(),
  created_at: z.string(),
})
export type LivingReviewHitRead = z.infer<typeof LivingReviewHitReadSchema>

export const LivingReviewRunResultSchema = z.object({
  job_id: z.string(),
  new_hits: z.number().int(),
  total_fetched: z.number().int(),
  ran_at: z.string(),
})
export type LivingReviewRunResult = z.infer<typeof LivingReviewRunResultSchema>

export type LivingReviewJobUpsert = {
  pubmed_query: string
  schedule: LivingSchedule
  enabled: boolean
}

export type LivingReviewJobPatch = Partial<LivingReviewJobUpsert>

export const livingReviewApi = {
  get: async (projectId: string): Promise<LivingReviewJobRead | null> => {
    try {
      const r = await api.get(`/api/projects/${projectId}/review/living`)
      return LivingReviewJobReadSchema.parse(r.data)
    } catch (e) {
      // 404 = no job configured yet — surface as null for the UI's empty state.
      if (e instanceof Error && /not found|404/i.test(e.message)) return null
      throw e
    }
  },
  upsert: async (
    projectId: string,
    body: LivingReviewJobUpsert,
  ): Promise<LivingReviewJobRead> => {
    const r = await api.post(`/api/projects/${projectId}/review/living`, body)
    return LivingReviewJobReadSchema.parse(r.data)
  },
  patch: async (
    projectId: string,
    body: LivingReviewJobPatch,
  ): Promise<LivingReviewJobRead> => {
    const r = await api.patch(`/api/projects/${projectId}/review/living`, body)
    return LivingReviewJobReadSchema.parse(r.data)
  },
  remove: async (projectId: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/review/living`)
  },
  runNow: async (projectId: string): Promise<LivingReviewRunResult> => {
    const r = await api.post(`/api/projects/${projectId}/review/living/run-now`)
    return LivingReviewRunResultSchema.parse(r.data)
  },
  listHits: async (
    projectId: string,
    decision?: LivingHitDecision,
  ): Promise<LivingReviewHitRead[]> => {
    const r = await api.get(`/api/projects/${projectId}/review/living/hits`, {
      params: decision ? { decision } : undefined,
    })
    return z.array(LivingReviewHitReadSchema).parse(r.data)
  },
  updateHit: async (
    projectId: string,
    hitId: string,
    decision: 'dismissed' | 'accepted',
  ): Promise<LivingReviewHitRead> => {
    const r = await api.patch(
      `/api/projects/${projectId}/review/living/hits/${hitId}`,
      { decision },
    )
    return LivingReviewHitReadSchema.parse(r.data)
  },
  importHitAsArticle: async (
    projectId: string,
    hitId: string,
  ): Promise<Article> => {
    const r = await api.post(
      `/api/projects/${projectId}/review/living/hits/${hitId}/import-as-article`,
    )
    return ArticleSchema.parse(r.data)
  },
}

// ── Phase 19 (MP19): MeSH + Search strategies + Narrative synthesis + Outcome instruments + Meta extensions ──

export const MeshSearchHitSchema = z.object({
  descriptor_ui: z.string(),
  descriptor_name: z.string(),
  scope_note: z.string().nullable().optional(),
  tree_numbers: z.array(z.string()).default([]),
  entry_terms: z.array(z.string()).default([]),
})
export type MeshSearchHit = z.infer<typeof MeshSearchHitSchema>

export const MeshSearchResponseSchema = z.object({
  query: z.string(),
  hits: z.array(MeshSearchHitSchema),
})
export type MeshSearchResponse = z.infer<typeof MeshSearchResponseSchema>

export const MeshTermReadSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  descriptor_ui: z.string(),
  descriptor_name: z.string(),
  scope_note: z.string().nullable(),
  tree_numbers: z.array(z.string()),
  entry_terms: z.array(z.string()),
  source: z.string(),
  created_at: z.string(),
})
export type MeshTermRead = z.infer<typeof MeshTermReadSchema>

export type MeshTermCreate = {
  descriptor_ui: string
  descriptor_name: string
  scope_note?: string | null
  tree_numbers: string[]
  entry_terms: string[]
  source?: 'user_added' | 'ncbi_lookup'
}

export const meshApi = {
  search: async (
    projectId: string,
    q: string,
    retmax = 20,
    cache = true,
  ): Promise<MeshSearchResponse> => {
    const r = await api.get(`/api/projects/${projectId}/review/mesh/search`, {
      params: { q, retmax, cache },
    })
    return MeshSearchResponseSchema.parse(r.data)
  },
  suggest: async (
    projectId: string,
    body: Partial<{
      population: string
      intervention: string
      comparator: string
      outcome: string
    }> = {},
    retmax = 10,
  ): Promise<MeshSearchResponse> => {
    const r = await api.post(
      `/api/projects/${projectId}/review/mesh/suggest`,
      body,
      { params: { retmax } },
    )
    return MeshSearchResponseSchema.parse(r.data)
  },
  listCache: async (projectId: string): Promise<MeshTermRead[]> => {
    const r = await api.get(`/api/projects/${projectId}/review/mesh/cache`)
    return z.array(MeshTermReadSchema).parse(r.data)
  },
  upsertCache: async (
    projectId: string,
    body: MeshTermCreate,
  ): Promise<MeshTermRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/review/mesh/cache`,
      body,
    )
    return MeshTermReadSchema.parse(r.data)
  },
  deleteCache: async (projectId: string, meshId: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/review/mesh/cache/${meshId}`)
  },
}

export const SearchDatabaseSchema = z.enum([
  'PubMed',
  'Embase',
  'Cochrane',
  'Web of Science',
  'Scopus',
  'Other',
])
export type SearchDatabase = z.infer<typeof SearchDatabaseSchema>

export const SearchStrategyReadSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  review_id: z.string(),
  name: z.string(),
  database: z.string(),
  query_text: z.string(),
  mesh_term_ids: z.array(z.string()),
  translated_from_id: z.string().nullable(),
  is_locked: z.boolean(),
  warnings: z.array(z.string()).nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type SearchStrategyRead = z.infer<typeof SearchStrategyReadSchema>

export type SearchStrategyCreate = {
  name: string
  database: SearchDatabase
  query_text: string
  mesh_term_ids: string[]
  translated_from_id?: string | null
  is_locked?: boolean
}

export type SearchStrategyUpdate = Partial<{
  name: string
  database: SearchDatabase
  query_text: string
  mesh_term_ids: string[]
  is_locked: boolean
}>

export const TranslationTargetSchema = z.enum(['embase', 'cochrane', 'wos'])
export type TranslationTarget = z.infer<typeof TranslationTargetSchema>

export const TranslateResponseSchema = z.object({
  translated_query: z.string(),
  warnings: z.array(z.string()),
  target: TranslationTargetSchema,
})
export type TranslateResponse = z.infer<typeof TranslateResponseSchema>

export const searchStrategiesApi = {
  list: async (projectId: string): Promise<SearchStrategyRead[]> => {
    const r = await api.get(
      `/api/projects/${projectId}/review/search-strategies`,
    )
    return z.array(SearchStrategyReadSchema).parse(r.data)
  },
  create: async (
    projectId: string,
    body: SearchStrategyCreate,
  ): Promise<SearchStrategyRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/review/search-strategies`,
      body,
    )
    return SearchStrategyReadSchema.parse(r.data)
  },
  update: async (
    projectId: string,
    id: string,
    body: SearchStrategyUpdate,
  ): Promise<SearchStrategyRead> => {
    const r = await api.patch(
      `/api/projects/${projectId}/review/search-strategies/${id}`,
      body,
    )
    return SearchStrategyReadSchema.parse(r.data)
  },
  remove: async (projectId: string, id: string): Promise<void> => {
    await api.delete(
      `/api/projects/${projectId}/review/search-strategies/${id}`,
    )
  },
  translate: async (
    projectId: string,
    id: string,
    to: TranslationTarget,
    persist = false,
  ): Promise<TranslateResponse> => {
    const r = await api.post(
      `/api/projects/${projectId}/review/search-strategies/${id}/translate`,
      null,
      { params: { to, persist } },
    )
    return TranslateResponseSchema.parse(r.data)
  },
}

export const NarrativeDirectionSchema = z.enum([
  'higher_better',
  'lower_better',
  'neutral',
])
export type NarrativeDirection = z.infer<typeof NarrativeDirectionSchema>

export const NarrativeSynthesisReadSchema = z.object({
  id: z.string(),
  review_id: z.string(),
  outcome_label: z.string(),
  instrument: z.string(),
  range_text: z.string().nullable(),
  direction: z.string(),
  narrative_html: z.string(),
  study_citations: z.array(z.string()),
  created_at: z.string(),
  updated_at: z.string(),
})
export type NarrativeSynthesisRead = z.infer<typeof NarrativeSynthesisReadSchema>

export type NarrativeSynthesisCreate = {
  outcome_label: string
  instrument: string
  range_text?: string | null
  direction?: NarrativeDirection
  narrative_html?: string
  study_citations: string[]
}

export type NarrativeSynthesisUpdate = Partial<NarrativeSynthesisCreate>

export const narrativeSynthesisApi = {
  list: async (projectId: string): Promise<NarrativeSynthesisRead[]> => {
    const r = await api.get(
      `/api/projects/${projectId}/review/narrative-synthesis`,
    )
    return z.array(NarrativeSynthesisReadSchema).parse(r.data)
  },
  create: async (
    projectId: string,
    body: NarrativeSynthesisCreate,
  ): Promise<NarrativeSynthesisRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/review/narrative-synthesis`,
      body,
    )
    return NarrativeSynthesisReadSchema.parse(r.data)
  },
  update: async (
    projectId: string,
    id: string,
    body: NarrativeSynthesisUpdate,
  ): Promise<NarrativeSynthesisRead> => {
    const r = await api.patch(
      `/api/projects/${projectId}/review/narrative-synthesis/${id}`,
      body,
    )
    return NarrativeSynthesisReadSchema.parse(r.data)
  },
  remove: async (projectId: string, id: string): Promise<void> => {
    await api.delete(
      `/api/projects/${projectId}/review/narrative-synthesis/${id}`,
    )
  },
  push: async (projectId: string): Promise<ManuscriptSection> => {
    const r = await api.post(
      `/api/projects/${projectId}/review/narrative-synthesis/push`,
    )
    return ManuscriptSectionSchema.parse(r.data)
  },
}

export const StudyValueEntrySchema = z.object({
  article_id: z.string(),
  group_label: z.string(),
  value: z.number().nullable().optional(),
  sd_or_ci: z.string().nullable().optional(),
  n: z.number().int().nullable().optional(),
})
export type StudyValueEntry = z.infer<typeof StudyValueEntrySchema>

export const OutcomeInstrumentReadSchema = z.object({
  id: z.string(),
  review_id: z.string(),
  outcome_label: z.string(),
  instrument_name: z.string(),
  score_range_low: z.number().nullable(),
  score_range_high: z.number().nullable(),
  mid: z.number().nullable(),
  study_values: z.array(z.record(z.string(), z.unknown())),
  created_at: z.string(),
})
export type OutcomeInstrumentRead = z.infer<typeof OutcomeInstrumentReadSchema>

export type OutcomeInstrumentCreate = {
  outcome_label: string
  instrument_name: string
  score_range_low?: number | null
  score_range_high?: number | null
  mid?: number | null
  study_values: StudyValueEntry[]
}

export type OutcomeInstrumentUpdate = Partial<OutcomeInstrumentCreate>

export const outcomeInstrumentsApi = {
  list: async (projectId: string): Promise<OutcomeInstrumentRead[]> => {
    const r = await api.get(
      `/api/projects/${projectId}/review/outcome-instruments`,
    )
    return z.array(OutcomeInstrumentReadSchema).parse(r.data)
  },
  create: async (
    projectId: string,
    body: OutcomeInstrumentCreate,
  ): Promise<OutcomeInstrumentRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/review/outcome-instruments`,
      body,
    )
    return OutcomeInstrumentReadSchema.parse(r.data)
  },
  update: async (
    projectId: string,
    id: string,
    body: OutcomeInstrumentUpdate,
  ): Promise<OutcomeInstrumentRead> => {
    const r = await api.patch(
      `/api/projects/${projectId}/review/outcome-instruments/${id}`,
      body,
    )
    return OutcomeInstrumentReadSchema.parse(r.data)
  },
  remove: async (projectId: string, id: string): Promise<void> => {
    await api.delete(
      `/api/projects/${projectId}/review/outcome-instruments/${id}`,
    )
  },
  push: async (projectId: string): Promise<ManuscriptSection> => {
    const r = await api.post(
      `/api/projects/${projectId}/review/outcome-instruments/push`,
    )
    return ManuscriptSectionSchema.parse(r.data)
  },
}

export const PublicationBiasTestSchema = z.object({
  method: z.string(),
  statistic: z.number().nullable(),
  p: z.number().nullable(),
  note: z.string().nullable().optional(),
})
export type PublicationBiasTest = z.infer<typeof PublicationBiasTestSchema>

export const PublicationBiasResponseSchema = z.object({
  metric: z.string(),
  k: z.number().int(),
  recommended: z.string(),
  tests: z.array(PublicationBiasTestSchema),
})
export type PublicationBiasResponse = z.infer<typeof PublicationBiasResponseSchema>

export const LeaveOneOutRowSchema = z.object({
  excluded_id: z.string(),
  pooled_effect: z.number(),
  ci_low: z.number(),
  ci_high: z.number(),
  i2: z.number(),
})
export type LeaveOneOutRow = z.infer<typeof LeaveOneOutRowSchema>

export const LeaveOneOutResponseSchema = z.object({
  model: z.string(),
  metric: z.string(),
  k: z.number().int(),
  rows: z.array(LeaveOneOutRowSchema),
})
export type LeaveOneOutResponse = z.infer<typeof LeaveOneOutResponseSchema>

export const SubgroupInteractionResponseSchema = z.object({
  q_between: z.number(),
  df: z.number().int(),
  p_interaction: z.number(),
})
export type SubgroupInteractionResponse = z.infer<typeof SubgroupInteractionResponseSchema>

export const MetaRegressionResponseSchema = z.object({
  intercept: z.number(),
  coef: z.number(),
  se: z.number(),
  p: z.number(),
  r2: z.number(),
  n: z.number().int(),
  bubble_plot_png_base64: z.string(),
})
export type MetaRegressionResponse = z.infer<typeof MetaRegressionResponseSchema>

export const metaExtensionsApi = {
  publicationBias: async (
    projectId: string,
    metaId: string,
  ): Promise<PublicationBiasResponse> => {
    const r = await api.get(
      `/api/projects/${projectId}/reviews/meta/${metaId}/publication-bias`,
    )
    return PublicationBiasResponseSchema.parse(r.data)
  },
  leaveOneOut: async (
    projectId: string,
    metaId: string,
  ): Promise<LeaveOneOutResponse> => {
    const r = await api.get(
      `/api/projects/${projectId}/reviews/meta/${metaId}/leave-one-out`,
    )
    return LeaveOneOutResponseSchema.parse(r.data)
  },
  leaveOneOutPngUrl: (projectId: string, metaId: string): string =>
    `${API_URL}/api/projects/${projectId}/reviews/meta/${metaId}/leave-one-out.png`,
  subgroupInteraction: async (
    projectId: string,
    metaId: string,
  ): Promise<SubgroupInteractionResponse> => {
    const r = await api.get(
      `/api/projects/${projectId}/reviews/meta/${metaId}/subgroup-interaction`,
    )
    return SubgroupInteractionResponseSchema.parse(r.data)
  },
  metaRegression: async (
    projectId: string,
    metaId: string,
    moderator: number[],
    moderator_label = 'Moderator',
  ): Promise<MetaRegressionResponse> => {
    const r = await api.post(
      `/api/projects/${projectId}/reviews/meta/${metaId}/meta-regression`,
      { moderator, moderator_label },
    )
    return MetaRegressionResponseSchema.parse(r.data)
  },
}

// ─── Phase 17 (MP17) — Stats depth ─────────────────────────────────────────

export interface PopulationDefinition {
  filter: string
  label: string
}

export interface AnalysisPopulation {
  id: string
  dataset_id: string
  name: string
  definition: PopulationDefinition
  study_assignment_field: string
  treatment_received_field: string | null
  created_at: string
}

export interface PopulationCreateBody {
  name: string
  definition: PopulationDefinition
  study_assignment_field: string
  treatment_received_field?: string | null
}

export const populationsApi = {
  list: async (projectId: string, datasetId: string): Promise<AnalysisPopulation[]> => {
    const r = await api.get(`/api/projects/${projectId}/datasets/${datasetId}/populations`)
    return r.data as AnalysisPopulation[]
  },
  create: async (
    projectId: string,
    datasetId: string,
    body: PopulationCreateBody,
  ): Promise<AnalysisPopulation> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/populations`,
      body,
    )
    return r.data as AnalysisPopulation
  },
  update: async (
    projectId: string,
    datasetId: string,
    populationId: string,
    body: Partial<PopulationCreateBody>,
  ): Promise<AnalysisPopulation> => {
    const r = await api.patch(
      `/api/projects/${projectId}/datasets/${datasetId}/populations/${populationId}`,
      body,
    )
    return r.data as AnalysisPopulation
  },
  delete: async (
    projectId: string,
    datasetId: string,
    populationId: string,
  ): Promise<void> => {
    await api.delete(
      `/api/projects/${projectId}/datasets/${datasetId}/populations/${populationId}`,
    )
  },
  preview: async (
    projectId: string,
    datasetId: string,
    populationId: string,
  ): Promise<{ n_before: number; n_after: number; head_rows: unknown[] }> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/populations/${populationId}/preview`,
    )
    return r.data
  },
}

export interface PostHocPair {
  pair: [string, string]
  mean_diff: number
  ci_low: number | null
  ci_high: number | null
  p_adj: number
  method: string
  n_a: number
  n_b: number
}

export const postHocApi = {
  run: async (
    projectId: string,
    analysisId: string,
    body: { method: 'tukey' | 'bonferroni' | 'dunns' | 'games_howell'; outcome: string; groups: string },
  ): Promise<{ method: string; n_groups: number; pairs: PostHocPair[] }> => {
    const r = await api.post(
      `/api/projects/${projectId}/analyses/${analysisId}/post-hoc`,
      body,
    )
    return r.data
  },
}

export interface MixedEffectsParams {
  outcome: string
  predictors: string[]
  cluster: string
  inner_cluster?: string | null
  reml?: boolean
  interaction_pair?: [string, string] | null
}

export const mixedEffectsApi = {
  // Reuses the standard analyses POST/createAndRun path with chosen_test = 'mixed_effects_lm'.
  buildVariables: (params: MixedEffectsParams) => ({ ...params }),
}

export interface ImputationRunRecord {
  id: string
  dataset_id: string
  method: string
  n_imputations: number
  seed: number
  target_cols: string[]
  pooled_summary: { method: string; per_column: Array<Record<string, number>>; n_imputations: number }
  created_at: string
}

export const imputationApi = {
  list: async (
    projectId: string,
    datasetId: string,
  ): Promise<ImputationRunRecord[]> => {
    const r = await api.get(`/api/projects/${projectId}/datasets/${datasetId}/imputation-runs`)
    return r.data as ImputationRunRecord[]
  },
  run: async (
    projectId: string,
    datasetId: string,
    body: {
      method: 'mice' | 'knn' | 'mean' | 'median' | 'last_observation'
      target_cols: string[]
      n_imputations?: number
      seed?: number
    },
  ): Promise<ImputationRunRecord> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/impute`,
      { n_imputations: 5, seed: 42, ...body },
    )
    return r.data as ImputationRunRecord
  },
}

export interface CACEResponse {
  cace_estimate: number
  se: number
  p: number
  compliance_rate: number
  n: number
}

export const caceApi = {
  run: async (
    projectId: string,
    analysisId: string,
    body: { outcome: string; assigned: string; received: string },
  ): Promise<CACEResponse> => {
    const r = await api.post(
      `/api/projects/${projectId}/analyses/${analysisId}/cace`,
      body,
    )
    return r.data as CACEResponse
  },
}

export interface SensitivityResponse {
  type: string
  effect_estimate: number | null
  p_value: number | null
  threshold: number | null
  n_imputed: number
  note: string
}

export const sensitivityApi = {
  run: async (
    projectId: string,
    analysisId: string,
    body: {
      type: 'worst_case' | 'best_case' | 'tipping_point'
      outcome: string
      group: string
      candidate_low?: number | null
      candidate_high?: number | null
      alpha?: number
    },
  ): Promise<SensitivityResponse> => {
    const r = await api.post(
      `/api/projects/${projectId}/analyses/${analysisId}/sensitivity`,
      body,
    )
    return r.data as SensitivityResponse
  },
}

export const irrApi = {
  fleiss: async (
    projectId: string,
    datasetId: string,
    matrix: number[][],
  ): Promise<{ kappa: number; z: number; p: number; n_subjects: number; n_raters: number; n_categories: number }> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/irr`,
      { method: 'fleiss', matrix },
    )
    return r.data
  },
  krippendorff: async (
    projectId: string,
    datasetId: string,
    ratings: (number | null)[][],
    level: 'nominal' | 'ordinal' | 'interval' = 'nominal',
  ): Promise<{ alpha: number; level: string; n_raters: number; n_items: number; n_pairable: number }> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/irr`,
      { method: 'krippendorff', ratings, level },
    )
    return r.data
  },
  weightedKappa: async (
    projectId: string,
    datasetId: string,
    rater1: number[],
    rater2: number[],
    weights: 'linear' | 'quadratic' = 'linear',
    n_bootstrap = 0,
  ): Promise<{ kappa: number; weights: string; n: number; ci_low: number | null; ci_high: number | null; se: number | null }> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/irr`,
      { method: 'weighted_kappa', rater1, rater2, weights, n_bootstrap, seed: 0 },
    )
    return r.data
  },
}

export interface InstrumentSpec {
  name: string
  abbreviation: string
  scale_low: number
  scale_high: number
  mid: number | null
  direction: 'higher_better' | 'lower_better' | 'neutral'
  category: string
  default_citation: string
}

export const instrumentsApi = {
  catalogue: async (): Promise<InstrumentSpec[]> => {
    const r = await api.get(`/api/instruments/catalogue`)
    return r.data.instruments as InstrumentSpec[]
  },
  bind: async (
    projectId: string,
    datasetId: string,
    variableId: string,
    instrumentKey: string | null,
  ): Promise<{ variable_id: string; instrument_key: string | null }> => {
    const r = await api.patch(
      `/api/projects/${projectId}/datasets/${datasetId}/variables/${variableId}/instrument-binding`,
      { instrument_key: instrumentKey },
    )
    return r.data
  },
}

export const analysisPlanLockApi = {
  lock: async (
    projectId: string,
    planId: string,
  ): Promise<{ plan_id: string; integrity_hash: string; locked_at: string }> => {
    const r = await api.post(`/api/projects/${projectId}/analysis-plans/${planId}/lock`)
    return r.data
  },
  forceUnlockPatch: async (
    projectId: string,
    planId: string,
    body: Record<string, unknown>,
  ): Promise<unknown> => {
    const r = await api.patch(`/api/projects/${projectId}/analysis-plans/${planId}`, {
      ...body,
      force_unlock: true,
    })
    return r.data
  },
}

// ── DEMO-FIX-A: standalone diagnostic-tests panel ─────────────────────

export const DiagnosticTestKeySchema = z.enum([
  'shapiro_wilk',
  'anderson_darling',
  'kolmogorov_smirnov',
  'dagostino_pearson',
  'levene',
  'bartlett',
])
export type DiagnosticTestKey = z.infer<typeof DiagnosticTestKeySchema>

export const DIAGNOSTIC_TEST_LABELS: Record<DiagnosticTestKey, string> = {
  shapiro_wilk: 'Shapiro-Wilk (normality)',
  anderson_darling: 'Anderson-Darling (normality)',
  kolmogorov_smirnov: 'Kolmogorov-Smirnov (vs normal)',
  dagostino_pearson: "D'Agostino-Pearson (normality)",
  levene: "Levene (equal variance, Brown-Forsythe)",
  bartlett: 'Bartlett (equal variance)',
}

/** Two-group / multi-group tests need a group column; single-sample tests don't. */
export const DIAGNOSTIC_NEEDS_GROUP: Record<DiagnosticTestKey, boolean> = {
  shapiro_wilk: false,
  anderson_darling: false,
  kolmogorov_smirnov: false,
  dagostino_pearson: false,
  levene: true,
  bartlett: true,
}

export const DiagnosticResultSchema = z.object({
  test_key: DiagnosticTestKeySchema,
  statistic: z.number(),
  p: z.number().nullable(),
  n: z.number().int(),
  interpretation: z.string(),
  ok: z.boolean(),
  critical_values: z.record(z.string(), z.number()).nullable().optional(),
  significance_levels: z.array(z.number()).nullable().optional(),
  k: z.number().int().nullable().optional(),
  center: z.string().nullable().optional(),
  extras: z.record(z.string(), z.unknown()).nullable().optional(),
})
export type DiagnosticResult = z.infer<typeof DiagnosticResultSchema>

export type DiagnosticRequest = {
  test_key: DiagnosticTestKey
  column_name: string
  group_column?: string | null
}

export const diagnosticsApi = {
  run: async (
    projectId: string,
    datasetId: string,
    body: DiagnosticRequest,
  ): Promise<DiagnosticResult> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/diagnostics/run`,
      body,
    )
    return DiagnosticResultSchema.parse(r.data)
  },
  qqPlot: async (
    projectId: string,
    datasetId: string,
    columnName: string,
    title?: string,
  ): Promise<string> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/diagnostics/qq-plot`,
      { column_name: columnName, title: title ?? null },
      { responseType: 'blob' },
    )
    return URL.createObjectURL(r.data as Blob)
  },
  histogram: async (
    projectId: string,
    datasetId: string,
    columnName: string,
    title?: string,
  ): Promise<string> => {
    const r = await api.post(
      `/api/projects/${projectId}/datasets/${datasetId}/diagnostics/histogram`,
      { column_name: columnName, title: title ?? null },
      { responseType: 'blob' },
    )
    return URL.createObjectURL(r.data as Blob)
  },
}

export const sapApi = {
  exportUrl: (projectId: string, planId: string, format: 'docx' | 'pdf'): string =>
    `/api/projects/${projectId}/analysis-plans/${planId}/sap?format=${format}`,
  download: async (
    projectId: string,
    planId: string,
    format: 'docx' | 'pdf' = 'docx',
  ): Promise<Blob> => {
    const r = await api.get(`/api/projects/${projectId}/analysis-plans/${planId}/sap`, {
      params: { format },
      responseType: 'blob',
    })
    return r.data as Blob
  },
}

// ─── Phase 18 (MP18) — Health Economics ───────────────────────────────────

export type EconomicCurrency = 'GBP' | 'USD' | 'EUR' | 'AUD' | 'CAD' | 'Other'
export type EconomicPerspective = 'patient' | 'healthcare_system' | 'societal'
export type UtilityValueSetKey =
  | 'EQ5D_3L_UK'
  | 'EQ5D_5L_UK'
  | 'EQ5D_Y_DUTCH'
  | 'SF6D'
  | 'direct'
export type EconomicCostRole =
  | 'unit_cost'
  | 'quantity'
  | 'cost_total'
  | 'utility_score'
  | 'qaly_weight'
  | 'time_to_event'
export type EconomicDominance =
  | 'dominant'
  | 'dominated'
  | 'icer_calculated'
  | 'northeast'
  | 'southwest'

export const costColumnBindingSchema = z.object({
  col: z.string().min(1),
  role: z.enum([
    'unit_cost',
    'quantity',
    'cost_total',
    'utility_score',
    'qaly_weight',
    'time_to_event',
  ] as const),
})
export type CostColumnBinding = z.infer<typeof costColumnBindingSchema>

export const economicResultSchema = z.object({
  id: z.string(),
  economic_analysis_id: z.string(),
  mean_cost_diff: z.number(),
  mean_qaly_diff: z.number(),
  icer: z.number().nullable(),
  dominance_status: z.string(),
  nmb_at_thresholds: z.record(z.number()),
  ceac_data: z.array(z.object({ wtp: z.number(), prob_costeffective: z.number() })),
  plane_bootstrap: z.array(z.object({ dCost: z.number(), dQALY: z.number() })),
  sensitivity: z.record(z.unknown()).nullable(),
  plane_png_uri: z.string(),
  ceac_png_uri: z.string(),
  created_at: z.string(),
})
export type EconomicResult = z.infer<typeof economicResultSchema>

export const economicAnalysisSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  dataset_id: z.string().nullable(),
  name: z.string(),
  currency: z.string(),
  time_horizon_months: z.number(),
  perspective: z.string(),
  discount_rate_costs: z.number(),
  discount_rate_qalys: z.number(),
  wtp_thresholds: z.array(z.number()),
  utility_value_set: z.string(),
  bootstrap_n: z.number(),
  seed: z.number(),
  treatment_col: z.string(),
  comparator_label: z.string(),
  intervention_label: z.string(),
  cost_columns: z.array(z.object({ col: z.string(), role: z.string() })),
  ai_interpretation: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  result: economicResultSchema.nullable().optional(),
})
export type EconomicAnalysis = z.infer<typeof economicAnalysisSchema>

export interface EconomicAnalysisCreateBody {
  name: string
  dataset_id?: string | null
  currency?: EconomicCurrency
  time_horizon_months?: number
  perspective?: EconomicPerspective
  discount_rate_costs?: number
  discount_rate_qalys?: number
  wtp_thresholds?: number[]
  utility_value_set?: UtilityValueSetKey
  bootstrap_n?: number
  seed?: number
  treatment_col: string
  comparator_label: string
  intervention_label: string
  cost_columns?: CostColumnBinding[]
}

export const utilityValueSetSchema = z.object({
  key: z.string(),
  label: z.string(),
  dimensions: z.array(z.string()),
  levels: z.number(),
  source_citation: z.string(),
  notes: z.string().nullable().optional(),
})
export type UtilityValueSetInfo = z.infer<typeof utilityValueSetSchema>

export const utilityValueSetsApi = {
  list: async (): Promise<UtilityValueSetInfo[]> => {
    const r = await api.get('/api/utility-value-sets')
    return z.array(utilityValueSetSchema).parse(r.data)
  },
}

export const economicAnalysesApi = {
  list: async (projectId: string): Promise<EconomicAnalysis[]> => {
    const r = await api.get(`/api/projects/${projectId}/economic-analyses`)
    return z.array(economicAnalysisSchema).parse(r.data)
  },
  get: async (projectId: string, id: string): Promise<EconomicAnalysis> => {
    const r = await api.get(`/api/projects/${projectId}/economic-analyses/${id}`)
    return economicAnalysisSchema.parse(r.data)
  },
  create: async (
    projectId: string,
    body: EconomicAnalysisCreateBody,
  ): Promise<EconomicAnalysis> => {
    const r = await api.post(`/api/projects/${projectId}/economic-analyses`, body)
    return economicAnalysisSchema.parse(r.data)
  },
  update: async (
    projectId: string,
    id: string,
    body: Partial<EconomicAnalysisCreateBody>,
  ): Promise<EconomicAnalysis> => {
    const r = await api.patch(
      `/api/projects/${projectId}/economic-analyses/${id}`,
      body,
    )
    return economicAnalysisSchema.parse(r.data)
  },
  delete: async (projectId: string, id: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/economic-analyses/${id}`)
  },
  run: async (projectId: string, id: string): Promise<EconomicAnalysis> => {
    const r = await api.post(`/api/projects/${projectId}/economic-analyses/${id}/run`)
    return economicAnalysisSchema.parse(r.data)
  },
  sensitivity: async (
    projectId: string,
    id: string,
    kind: 'psa' | 'dsa' | 'scenario',
    body: {
      parameter_distributions?: Record<string, Record<string, unknown>>
      parameter_ranges?: Record<string, { low: number; high: number }>
      scenarios?: Array<{ name: string; overrides: Record<string, number> }>
      n_psa?: number
      seed?: number
    },
  ): Promise<EconomicAnalysis> => {
    const r = await api.post(
      `/api/projects/${projectId}/economic-analyses/${id}/sensitivity`,
      body,
      { params: { type: kind } },
    )
    return economicAnalysisSchema.parse(r.data)
  },
  interpret: async (projectId: string, id: string): Promise<EconomicAnalysis> => {
    const r = await api.post(
      `/api/projects/${projectId}/economic-analyses/${id}/interpret`,
    )
    return economicAnalysisSchema.parse(r.data)
  },
  push: async (
    projectId: string,
    id: string,
    section = 'Results',
  ): Promise<unknown> => {
    const r = await api.post(
      `/api/projects/${projectId}/economic-analyses/${id}/push`,
      { section },
    )
    return r.data
  },
  cheersReport: async (
    projectId: string,
    id: string,
    format: 'docx' | 'pdf' = 'docx',
  ): Promise<Blob> => {
    const r = await api.get(
      `/api/projects/${projectId}/economic-analyses/${id}/cheers-report`,
      { params: { format }, responseType: 'blob' },
    )
    return r.data as Blob
  },
}

// ── Phase 20 (MP20): Interactive reporting checklists ────────────────────

export const ChecklistItemStatusSchema = z.enum(['pass', 'fail', 'unclear', 'na'])
export type ChecklistItemStatus = z.infer<typeof ChecklistItemStatusSchema>

export const ChecklistCatalogueItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string(),
  section_hint: z.string(),
})
export type ChecklistCatalogueItem = z.infer<typeof ChecklistCatalogueItemSchema>

export const ChecklistCatalogueSummarySchema = z.object({
  key: z.string(),
  name: z.string(),
  description: z.string(),
  version: z.string(),
  default_section: z.string(),
  item_count: z.number(),
})
export type ChecklistCatalogueSummary = z.infer<typeof ChecklistCatalogueSummarySchema>

export const ChecklistCatalogueReadSchema = z.object({
  key: z.string(),
  name: z.string(),
  description: z.string(),
  version: z.string(),
  default_section: z.string(),
  items: z.array(ChecklistCatalogueItemSchema),
})
export type ChecklistCatalogueRead = z.infer<typeof ChecklistCatalogueReadSchema>

export const ChecklistRunItemSchema = z.object({
  item_id: z.string(),
  item_text: z.string(),
  status: ChecklistItemStatusSchema,
  comment: z.string(),
  mapped_section: z.string().nullable(),
  mapped_text_excerpt: z.string().nullable(),
})
export type ChecklistRunItem = z.infer<typeof ChecklistRunItemSchema>

export const ChecklistRunReadSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  checklist_key: z.string(),
  title: z.string(),
  items: z.array(ChecklistRunItemSchema),
  overall_compliance_pct: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type ChecklistRunRead = z.infer<typeof ChecklistRunReadSchema>

export const ChecklistRunSummarySchema = z.object({
  id: z.string(),
  project_id: z.string(),
  checklist_key: z.string(),
  title: z.string(),
  overall_compliance_pct: z.number(),
  item_count: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
})
export type ChecklistRunSummary = z.infer<typeof ChecklistRunSummarySchema>

export type ChecklistRunItemPatch = {
  status?: ChecklistItemStatus
  comment?: string
  mapped_section?: string | null
  mapped_text_excerpt?: string | null
}

export const checklistsApi = {
  listCatalogue: async (): Promise<ChecklistCatalogueSummary[]> => {
    const r = await api.get('/api/checklists/catalogue')
    return z.array(ChecklistCatalogueSummarySchema).parse(r.data)
  },
  getCatalogue: async (key: string): Promise<ChecklistCatalogueRead> => {
    const r = await api.get(`/api/checklists/catalogue/${key}`)
    return ChecklistCatalogueReadSchema.parse(r.data)
  },
  listRuns: async (projectId: string): Promise<ChecklistRunSummary[]> => {
    const r = await api.get(`/api/projects/${projectId}/checklists`)
    return z.array(ChecklistRunSummarySchema).parse(r.data)
  },
  createRun: async (
    projectId: string,
    body: { checklist_key: string; title: string },
  ): Promise<ChecklistRunRead> => {
    const r = await api.post(`/api/projects/${projectId}/checklists`, body)
    return ChecklistRunReadSchema.parse(r.data)
  },
  getRun: async (
    projectId: string,
    runId: string,
  ): Promise<ChecklistRunRead> => {
    const r = await api.get(`/api/projects/${projectId}/checklists/${runId}`)
    return ChecklistRunReadSchema.parse(r.data)
  },
  patchItem: async (
    projectId: string,
    runId: string,
    itemId: string,
    patch: ChecklistRunItemPatch,
  ): Promise<ChecklistRunRead> => {
    const r = await api.patch(
      `/api/projects/${projectId}/checklists/${runId}/items/${itemId}`,
      patch,
    )
    return ChecklistRunReadSchema.parse(r.data)
  },
  autoCheck: async (
    projectId: string,
    runId: string,
  ): Promise<ChecklistRunRead> => {
    const r = await api.post(
      `/api/projects/${projectId}/checklists/${runId}/auto-check`,
    )
    return ChecklistRunReadSchema.parse(r.data)
  },
  exportRun: async (
    projectId: string,
    runId: string,
    format: 'pdf' | 'docx' = 'pdf',
  ): Promise<Blob> => {
    const r = await api.post(
      `/api/projects/${projectId}/checklists/${runId}/export`,
      undefined,
      { params: { format }, responseType: 'blob' },
    )
    return r.data as Blob
  },
  deleteRun: async (projectId: string, runId: string): Promise<void> => {
    await api.delete(`/api/projects/${projectId}/checklists/${runId}`)
  },
}
