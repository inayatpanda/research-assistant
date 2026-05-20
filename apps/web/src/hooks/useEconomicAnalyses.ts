import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  economicAnalysesApi,
  utilityValueSetsApi,
  type EconomicAnalysis,
  type EconomicAnalysisCreateBody,
  type UtilityValueSetInfo,
} from '@/lib/api'

export function useEconomicAnalyses(projectId: string | null) {
  return useQuery<EconomicAnalysis[]>({
    queryKey: ['economic-analyses', projectId],
    queryFn: () => economicAnalysesApi.list(projectId as string),
    enabled: !!projectId,
  })
}

export function useEconomicAnalysis(
  projectId: string | null,
  analysisId: string | null,
) {
  return useQuery<EconomicAnalysis>({
    queryKey: ['economic-analysis', projectId, analysisId],
    queryFn: () =>
      economicAnalysesApi.get(projectId as string, analysisId as string),
    enabled: !!projectId && !!analysisId,
  })
}

export function useCreateEconomicAnalysis(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: EconomicAnalysisCreateBody) =>
      economicAnalysesApi.create(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['economic-analyses', projectId] })
    },
  })
}

export function useUpdateEconomicAnalysis(projectId: string, analysisId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Partial<EconomicAnalysisCreateBody>) =>
      economicAnalysesApi.update(projectId, analysisId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['economic-analyses', projectId] })
      qc.invalidateQueries({
        queryKey: ['economic-analysis', projectId, analysisId],
      })
    },
  })
}

export function useDeleteEconomicAnalysis(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => economicAnalysesApi.delete(projectId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['economic-analyses', projectId] })
    },
  })
}

export function useRunEconomicAnalysis(projectId: string, analysisId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => economicAnalysesApi.run(projectId, analysisId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['economic-analyses', projectId] })
      qc.invalidateQueries({
        queryKey: ['economic-analysis', projectId, analysisId],
      })
    },
  })
}

export function useInterpretEconomicAnalysis(
  projectId: string,
  analysisId: string,
) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => economicAnalysesApi.interpret(projectId, analysisId),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ['economic-analysis', projectId, analysisId],
      })
    },
  })
}

export function useRunEconomicSensitivity(
  projectId: string,
  analysisId: string,
) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      kind,
      body,
    }: {
      kind: 'psa' | 'dsa' | 'scenario'
      body: Parameters<typeof economicAnalysesApi.sensitivity>[3]
    }) => economicAnalysesApi.sensitivity(projectId, analysisId, kind, body),
    onSuccess: () => {
      qc.invalidateQueries({
        queryKey: ['economic-analysis', projectId, analysisId],
      })
    },
  })
}

export function usePushEconomicAnalysis(projectId: string, analysisId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (section: string = 'Results') =>
      economicAnalysesApi.push(projectId, analysisId, section),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['manuscript', projectId] })
    },
  })
}

export function useUtilityValueSets() {
  return useQuery<UtilityValueSetInfo[]>({
    queryKey: ['utility-value-sets'],
    queryFn: () => utilityValueSetsApi.list(),
    staleTime: 1000 * 60 * 30, // static catalogue — cache 30 min
  })
}
