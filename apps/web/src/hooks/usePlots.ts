/**
 * Phase 13.5 (MP13.5) — React Query hooks for the saved-plots workspace.
 *
 * The list query is keyed on (projectId, datasetId) so a fresh plot is
 * picked up immediately after create / regenerate / delete.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'

import { plotsApi, type PlotCreate } from '@/lib/api'

const key = (projectId: string, datasetId: string) =>
  ['plots', projectId, datasetId] as const

export function usePlots(
  projectId: string | undefined,
  datasetId: string | undefined,
) {
  return useQuery({
    queryKey: ['plots', projectId, datasetId],
    queryFn: () => plotsApi.list(projectId!, datasetId!),
    enabled: !!projectId && !!datasetId,
  })
}

export function useCreatePlot(projectId: string, datasetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: PlotCreate) =>
      plotsApi.create(projectId, datasetId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: key(projectId, datasetId) })
    },
  })
}

export function useDeletePlot(projectId: string, datasetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (plotId: string) => plotsApi.delete(projectId, plotId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: key(projectId, datasetId) })
    },
  })
}

export function useRegeneratePlot(projectId: string, datasetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (plotId: string) => plotsApi.regenerate(projectId, plotId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: key(projectId, datasetId) })
    },
  })
}
