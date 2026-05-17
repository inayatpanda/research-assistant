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
