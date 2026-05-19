import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  livingReviewApi,
  type LivingHitDecision,
  type LivingReviewHitRead,
  type LivingReviewJobPatch,
  type LivingReviewJobRead,
  type LivingReviewJobUpsert,
} from '@/lib/api'

const jobKey = (projectId: string | null) => ['living-review', projectId]
const hitsKey = (projectId: string | null, decision: LivingHitDecision | undefined) =>
  ['living-review-hits', projectId, decision ?? 'all']

export function useLivingReview(projectId: string | null) {
  return useQuery<LivingReviewJobRead | null>({
    queryKey: jobKey(projectId),
    queryFn: () => livingReviewApi.get(projectId as string),
    enabled: !!projectId,
  })
}

export function useUpsertLivingReview(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: LivingReviewJobUpsert) =>
      livingReviewApi.upsert(projectId, body),
    onSuccess: (data) => {
      qc.setQueryData(jobKey(projectId), data)
    },
  })
}

export function usePatchLivingReview(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: LivingReviewJobPatch) =>
      livingReviewApi.patch(projectId, body),
    onSuccess: (data) => {
      qc.setQueryData(jobKey(projectId), data)
    },
  })
}

export function useDeleteLivingReview(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => livingReviewApi.remove(projectId),
    onSuccess: () => {
      qc.setQueryData(jobKey(projectId), null)
      qc.invalidateQueries({ queryKey: ['living-review-hits', projectId] })
    },
  })
}

export function useRunLivingReviewNow(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => livingReviewApi.runNow(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: jobKey(projectId) })
      qc.invalidateQueries({ queryKey: ['living-review-hits', projectId] })
    },
  })
}

export function useLivingReviewHits(
  projectId: string | null,
  decision: LivingHitDecision | undefined,
) {
  return useQuery<LivingReviewHitRead[]>({
    queryKey: hitsKey(projectId, decision),
    queryFn: () =>
      livingReviewApi.listHits(projectId as string, decision),
    enabled: !!projectId,
  })
}

export function useUpdateLivingReviewHit(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ hitId, decision }: { hitId: string; decision: 'dismissed' | 'accepted' }) =>
      livingReviewApi.updateHit(projectId, hitId, decision),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['living-review-hits', projectId] })
    },
  })
}

export function useImportLivingReviewHit(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (hitId: string) =>
      livingReviewApi.importHitAsArticle(projectId, hitId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['articles', projectId] })
      qc.invalidateQueries({ queryKey: ['living-review-hits', projectId] })
    },
  })
}
