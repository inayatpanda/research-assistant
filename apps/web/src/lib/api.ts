import axios, { AxiosError } from 'axios'
import { z } from 'zod'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8787'

export const api = axios.create({
  baseURL: API_URL,
  timeout: 30_000,
})

api.interceptors.response.use(
  (r) => r,
  (error: AxiosError) => {
    const detail =
      (error.response?.data as { detail?: unknown } | undefined)?.detail ??
      error.message ??
      'Network error'
    return Promise.reject(new Error(typeof detail === 'string' ? detail : 'Request failed'))
  },
)

// --- Schemas (runtime + types) ---

export const ProjectSchema = z.object({
  id: z.string(),
  user_id: z.string(),
  title: z.string(),
  study_type: z.string(),
  citation_style: z.enum(['vancouver', 'apa', 'harvard']),
  ai_provider: z.enum(['gemini', 'claude', 'openai']),
  target_journal: z.string().nullable(),
  prospero_number: z.string().nullable(),
  clinicaltrials_number: z.string().nullable(),
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
  ]),
  citation_style: z.enum(['vancouver', 'apa', 'harvard']).optional(),
  ai_provider: z.enum(['gemini', 'claude', 'openai']).optional(),
  target_journal: z.string().optional(),
  prospero_number: z.string().optional(),
  clinicaltrials_number: z.string().optional(),
})
export type ProjectCreate = z.infer<typeof ProjectCreateSchema>

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
  file_ref: StorageRefSchema.nullable(),
  file_type: z.string().nullable(),
  study_design: z.string().nullable(),
  review_status: ReviewStatusSchema,
  exclusion_reason: z.string().nullable(),
  conflict_of_interest: z.string().nullable(),
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
    const r = await api.post(`/api/projects/${projectId}/articles/upload`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
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
})
export type DatasetVariable = z.infer<typeof DatasetVariableSchema>

export const DatasetSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  filename: z.string(),
  file_type: z.string(),
  n_rows: z.number().int(),
  n_columns: z.number().int(),
  created_at: z.string(),
  variables: z.array(DatasetVariableSchema),
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
    const r = await api.post(`/api/projects/${projectId}/datasets`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
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
}
