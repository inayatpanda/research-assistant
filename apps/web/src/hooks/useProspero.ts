import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { prosperoApi, type ProsperoDraftRead } from '@/lib/api'

export function useProspero(projectId: string | null) {
  return useQuery<ProsperoDraftRead>({
    queryKey: ['prospero', projectId],
    queryFn: () => prosperoApi.get(projectId as string),
    enabled: !!projectId,
  })
}

export function useUpdateProspero(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (fields: Record<string, string>) =>
      prosperoApi.patch(projectId, fields),
    onSuccess: (data) => {
      qc.setQueryData(['prospero', projectId], data)
    },
  })
}

export function useExportProspero(projectId: string) {
  return useMutation({
    mutationFn: () => prosperoApi.export(projectId),
  })
}
