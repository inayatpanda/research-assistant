import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  extractionApi,
  robApi,
  reviewsApi,
  screeningApi,
  searchApi,
  type ExtractionRecordCreate,
  type ExtractionRecordUpdate,
  type ReviewStage,
  type ReviewUpdate,
  type RoBAssessmentCreate,
  type RoBAssessmentUpdate,
  type ScreeningRecordCreate,
  type ScreeningRecordUpdate,
  type SearchRecordCreate,
  type SearchRecordUpdate,
} from '@/lib/api'

// --- Review (PICO + eligibility) ---

export function useReview(projectId: string | undefined) {
  return useQuery({
    queryKey: ['review', projectId],
    queryFn: () => reviewsApi.get(projectId!),
    enabled: !!projectId,
  })
}

export function useUpdateReview(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ReviewUpdate) => reviewsApi.patch(projectId, body),
    onSuccess: (data) => {
      qc.setQueryData(['review', projectId], data)
    },
  })
}

// --- Search ---

export function useSearchRecords(projectId: string | undefined) {
  return useQuery({
    queryKey: ['review-search', projectId],
    queryFn: () => searchApi.list(projectId!),
    enabled: !!projectId,
  })
}

export function useCreateSearch(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: SearchRecordCreate) => searchApi.create(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-search', projectId] })
      qc.invalidateQueries({ queryKey: ['review-prisma', projectId] })
    },
  })
}

export function useUpdateSearch(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: SearchRecordUpdate }) =>
      searchApi.update(projectId, id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-search', projectId] })
      qc.invalidateQueries({ queryKey: ['review-prisma', projectId] })
    },
  })
}

export function useDeleteSearch(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => searchApi.remove(projectId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-search', projectId] })
      qc.invalidateQueries({ queryKey: ['review-prisma', projectId] })
    },
  })
}

export function usePushSearch(projectId: string) {
  return useMutation({ mutationFn: () => searchApi.push(projectId) })
}

// --- Screening ---

export function useScreening(
  projectId: string | undefined,
  stage: ReviewStage | undefined,
) {
  return useQuery({
    queryKey: ['review-screening', projectId, stage ?? 'all'],
    queryFn: () => screeningApi.list(projectId!, stage),
    enabled: !!projectId,
  })
}

export function useUpsertScreening(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ScreeningRecordCreate) =>
      screeningApi.upsert(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-screening', projectId] })
      qc.invalidateQueries({ queryKey: ['review-prisma', projectId] })
    },
  })
}

export function useUpdateScreening(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: ScreeningRecordUpdate }) =>
      screeningApi.update(projectId, id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-screening', projectId] })
      qc.invalidateQueries({ queryKey: ['review-prisma', projectId] })
    },
  })
}

export function useAiSuggestScreening(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (screeningId: string) =>
      screeningApi.aiSuggest(projectId, screeningId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['review-screening', projectId] })
    },
  })
}

// --- RoB ---

export function useRoBTools(projectId: string | undefined) {
  return useQuery({
    queryKey: ['rob-tools', projectId],
    queryFn: () => robApi.tools(projectId!),
    enabled: !!projectId,
    staleTime: Infinity,
  })
}

export function useRoBAssessments(projectId: string | undefined) {
  return useQuery({
    queryKey: ['rob-assessments', projectId],
    queryFn: () => robApi.list(projectId!),
    enabled: !!projectId,
  })
}

export function useUpsertRoB(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: RoBAssessmentCreate) => robApi.upsert(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rob-assessments', projectId] })
    },
  })
}

export function useUpdateRoB(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: RoBAssessmentUpdate }) =>
      robApi.update(projectId, id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rob-assessments', projectId] })
    },
  })
}

export function usePushRoB(projectId: string) {
  return useMutation({ mutationFn: () => robApi.push(projectId) })
}

// --- Extraction ---

export function useExtractionSchema(projectId: string | undefined) {
  return useQuery({
    queryKey: ['extraction-schema', projectId],
    queryFn: () => extractionApi.schema(projectId!),
    enabled: !!projectId,
    staleTime: Infinity,
  })
}

export function useExtractionRecords(projectId: string | undefined) {
  return useQuery({
    queryKey: ['extraction-records', projectId],
    queryFn: () => extractionApi.list(projectId!),
    enabled: !!projectId,
  })
}

export function useUpsertExtraction(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ExtractionRecordCreate) =>
      extractionApi.upsert(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['extraction-records', projectId] })
    },
  })
}

export function useUpdateExtraction(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: ExtractionRecordUpdate }) =>
      extractionApi.update(projectId, id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['extraction-records', projectId] })
    },
  })
}

export function usePushExtraction(projectId: string) {
  return useMutation({ mutationFn: () => extractionApi.push(projectId) })
}

// --- PRISMA ---

export function usePrisma(projectId: string | undefined) {
  return useQuery({
    queryKey: ['review-prisma', projectId],
    queryFn: () => reviewsApi.prisma(projectId!),
    enabled: !!projectId,
  })
}

export function usePushPrisma(projectId: string) {
  return useMutation({ mutationFn: () => reviewsApi.pushPrisma(projectId) })
}
