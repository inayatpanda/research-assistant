import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  reviewerResponseApi,
  type ReviewerResponseCreate,
  type ReviewerResponseRead,
  type ReviewerResponseUpdate,
} from '@/lib/api'

export function useReviewerResponses(projectId: string | null) {
  return useQuery<ReviewerResponseRead[]>({
    queryKey: ['reviewer-responses', projectId],
    queryFn: () => reviewerResponseApi.list(projectId as string),
    enabled: !!projectId,
  })
}

export function useCreateReviewerResponse(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: ReviewerResponseCreate) =>
      reviewerResponseApi.create(projectId, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['reviewer-responses', projectId] }),
  })
}

export function useUpdateReviewerResponse(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      responseId,
      body,
    }: {
      responseId: string
      body: ReviewerResponseUpdate
    }) => reviewerResponseApi.update(projectId, responseId, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['reviewer-responses', projectId] }),
  })
}

export function useDeleteReviewerResponse(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (responseId: string) =>
      reviewerResponseApi.delete(projectId, responseId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['reviewer-responses', projectId] }),
  })
}
