import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  commentsApi,
  type CommentCreate,
  type CommentRead,
  type CommentSection,
  type CommentUpdate,
} from '@/lib/api'

export function useComments(
  projectId: string | null,
  filters?: { section?: CommentSection; resolved?: boolean },
) {
  return useQuery<CommentRead[]>({
    queryKey: [
      'comments',
      projectId,
      filters?.section ?? 'all',
      filters?.resolved ?? 'any',
    ],
    queryFn: () => commentsApi.list(projectId as string, filters),
    enabled: !!projectId,
  })
}

export function useCreateComment(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CommentCreate) => commentsApi.create(projectId, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['comments', projectId] }),
  })
}

export function useUpdateComment(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: CommentUpdate }) =>
      commentsApi.update(projectId, id, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['comments', projectId] }),
  })
}

export function useDeleteComment(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => commentsApi.delete(projectId, id),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['comments', projectId] }),
  })
}
