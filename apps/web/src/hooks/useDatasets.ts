import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { datasetsApi, type VariableType } from '@/lib/api'

export function useDatasets(projectId: string | undefined) {
  return useQuery({
    queryKey: ['datasets', projectId],
    queryFn: () => datasetsApi.list(projectId!),
    enabled: !!projectId,
  })
}

export function useDataset(
  projectId: string | undefined,
  datasetId: string | undefined,
) {
  return useQuery({
    queryKey: ['dataset', projectId, datasetId],
    queryFn: () => datasetsApi.get(projectId!, datasetId!),
    enabled: !!projectId && !!datasetId,
  })
}

export function useUploadDataset(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => datasetsApi.upload(projectId, file),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['datasets', projectId] })
    },
  })
}

export function useDeleteDataset(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (datasetId: string) => datasetsApi.delete(projectId, datasetId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['datasets', projectId] })
    },
  })
}

export function useUpdateVariableType(projectId: string, datasetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { variableId: string; userType: VariableType | null }) =>
      datasetsApi.updateVariable(projectId, datasetId, vars.variableId, vars.userType),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['dataset', projectId, datasetId] })
      qc.invalidateQueries({ queryKey: ['datasets', projectId] })
    },
  })
}
