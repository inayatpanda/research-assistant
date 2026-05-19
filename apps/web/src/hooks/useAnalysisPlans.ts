/**
 * Phase 13.5 (MP13.5) — React Query hooks for analysis plans + plan runs.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'

import {
  analysisPlansApi,
  type AnalysisPlanCreate,
  type AnalysisPlanUpdate,
} from '@/lib/api'

const plansKey = (projectId: string) => ['analysis-plans', projectId] as const
const runsKey = (projectId: string, planId: string) =>
  ['analysis-plan-runs', projectId, planId] as const

export function useAnalysisPlans(projectId: string | undefined) {
  return useQuery({
    queryKey: ['analysis-plans', projectId],
    queryFn: () => analysisPlansApi.list(projectId!),
    enabled: !!projectId,
  })
}

export function useCreateAnalysisPlan(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: AnalysisPlanCreate) =>
      analysisPlansApi.create(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: plansKey(projectId) })
    },
  })
}

export function useUpdateAnalysisPlan(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      planId,
      body,
    }: {
      planId: string
      body: AnalysisPlanUpdate
    }) => analysisPlansApi.update(projectId, planId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: plansKey(projectId) })
    },
  })
}

export function useDeleteAnalysisPlan(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (planId: string) => analysisPlansApi.delete(projectId, planId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: plansKey(projectId) })
    },
  })
}

export function useRunAnalysisPlan(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      planId,
      datasetId,
    }: {
      planId: string
      datasetId: string
    }) => analysisPlansApi.run(projectId, planId, datasetId),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: runsKey(projectId, vars.planId) })
    },
  })
}

export function useAnalysisPlanRuns(
  projectId: string | undefined,
  planId: string | undefined,
) {
  return useQuery({
    queryKey: ['analysis-plan-runs', projectId, planId],
    queryFn: () => analysisPlansApi.listRuns(projectId!, planId!),
    enabled: !!projectId && !!planId,
  })
}
