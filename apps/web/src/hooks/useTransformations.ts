import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'

import {
  transformationsApi,
  type TransformationCreate,
  type TransformationUpdate,
} from '@/lib/api'

const key = (projectId: string, datasetId: string) =>
  ['transformations', projectId, datasetId] as const

export function useTransformations(
  projectId: string | undefined,
  datasetId: string | undefined,
) {
  return useQuery({
    queryKey: ['transformations', projectId, datasetId],
    queryFn: () => transformationsApi.list(projectId!, datasetId!),
    enabled: !!projectId && !!datasetId,
  })
}

export function useAddTransformation(projectId: string, datasetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: TransformationCreate) =>
      transformationsApi.add(projectId, datasetId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: key(projectId, datasetId) })
    },
  })
}

export function useUpdateTransformation(
  projectId: string,
  datasetId: string,
) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      transformationId,
      body,
    }: {
      transformationId: string
      body: TransformationUpdate
    }) =>
      transformationsApi.update(projectId, datasetId, transformationId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: key(projectId, datasetId) })
    },
  })
}

export function useDeleteTransformation(
  projectId: string,
  datasetId: string,
) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (transformationId: string) =>
      transformationsApi.delete(projectId, datasetId, transformationId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: key(projectId, datasetId) })
    },
  })
}

export function useReorderTransformations(
  projectId: string,
  datasetId: string,
) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (ids: string[]) =>
      transformationsApi.reorder(projectId, datasetId, ids),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: key(projectId, datasetId) })
    },
  })
}
