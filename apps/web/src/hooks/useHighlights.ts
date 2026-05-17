import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  highlightsApi,
  type Highlight,
  type HighlightCreate,
  type HighlightUpdate,
} from '@/lib/api'

export function useHighlights(articleId: string | undefined) {
  return useQuery({
    queryKey: ['highlights', articleId],
    queryFn: () => highlightsApi.list(articleId!),
    enabled: !!articleId,
  })
}

export function useCreateHighlight(articleId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: HighlightCreate): Promise<Highlight> =>
      highlightsApi.create(articleId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['highlights', articleId] }),
  })
}

export function useUpdateHighlight(articleId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (vars: { id: string; patch: HighlightUpdate }) =>
      highlightsApi.update(vars.id, vars.patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['highlights', articleId] }),
  })
}

export function useDeleteHighlight(articleId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => highlightsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['highlights', articleId] }),
  })
}

export function useSummariseHighlight(articleId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => highlightsApi.summarise(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['highlights', articleId] }),
  })
}
