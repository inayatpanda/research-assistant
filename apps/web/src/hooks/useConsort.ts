import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { consortApi, type ConsortDataPayload, type ConsortGetResponse } from '@/lib/api'

export function useConsort(projectId: string | null) {
  return useQuery<ConsortGetResponse>({
    queryKey: ['consort', projectId],
    queryFn: () => consortApi.get(projectId as string),
    enabled: !!projectId,
  })
}

export function useUpdateConsort(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ConsortDataPayload) => consortApi.patch(projectId, body),
    onSuccess: (resp) => qc.setQueryData(['consort', projectId], resp),
  })
}

export function usePushConsort(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => consortApi.push(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['manuscript', projectId] })
    },
  })
}
