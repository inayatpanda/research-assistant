import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  coverLetterApi,
  type CoverLetterDraftRequest,
  type CoverLetterRead,
  type CoverLetterUpdate,
} from '@/lib/api'

export function useCoverLetter(projectId: string | null) {
  return useQuery<CoverLetterRead>({
    queryKey: ['cover-letter', projectId],
    queryFn: () => coverLetterApi.get(projectId as string),
    enabled: !!projectId,
  })
}

export function useUpdateCoverLetter(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CoverLetterUpdate) =>
      coverLetterApi.update(projectId, body),
    onSuccess: (data) =>
      qc.setQueryData(['cover-letter', projectId], data),
  })
}

export function useDraftCoverLetter(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CoverLetterDraftRequest = {}) =>
      coverLetterApi.draft(projectId, body),
    onSuccess: (data) =>
      qc.setQueryData(['cover-letter', projectId], data),
  })
}
