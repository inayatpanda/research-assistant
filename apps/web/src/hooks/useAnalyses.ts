import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  analysesApi,
  type AnalysisCreate,
  type RecommendationRequest,
} from '@/lib/api'

export function useAnalysesForDataset(
  projectId: string | undefined,
  datasetId: string | undefined,
) {
  return useQuery({
    queryKey: ['analyses', projectId, datasetId],
    queryFn: () => analysesApi.listForDataset(projectId!, datasetId!),
    enabled: !!projectId && !!datasetId,
  })
}

export function useRecommendAnalysis(projectId: string, datasetId: string) {
  return useMutation({
    mutationFn: (body: RecommendationRequest) =>
      analysesApi.recommend(projectId, datasetId, body),
  })
}

export function useCreateAnalysis(projectId: string, datasetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: AnalysisCreate) =>
      analysesApi.create(projectId, datasetId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['analyses', projectId, datasetId] })
    },
  })
}

export function useRunAnalysis(projectId: string, datasetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (analysisId: string) => analysesApi.run(projectId, analysisId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['analyses', projectId, datasetId] })
    },
  })
}

export function useInterpretAnalysis(projectId: string, datasetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (analysisId: string) => analysesApi.interpret(projectId, analysisId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['analyses', projectId, datasetId] })
    },
  })
}

export function usePushToManuscript(projectId: string) {
  return useMutation({
    mutationFn: (analysisId: string) =>
      analysesApi.pushToManuscript(projectId, analysisId),
  })
}

export function useDeleteAnalysis(projectId: string, datasetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (analysisId: string) => analysesApi.delete(projectId, analysisId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['analyses', projectId, datasetId] })
    },
  })
}

/** DEMO-FIX-C — Edit per-chart x/y/title overrides + re-render. */
export function useUpdateChartLabels(projectId: string, datasetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (args: {
      analysisId: string
      x_label_override?: string | null
      y_label_override?: string | null
      title_override?: string | null
    }) => {
      const { analysisId, ...body } = args
      return analysesApi.updateChartLabels(projectId, analysisId, body)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['analyses', projectId, datasetId] })
    },
  })
}
