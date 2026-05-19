import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  searchStrategiesApi,
  type SearchStrategyCreate,
  type SearchStrategyRead,
  type SearchStrategyUpdate,
  type TranslationTarget,
} from '@/lib/api'

export function useSearchStrategies(projectId: string | null) {
  return useQuery<SearchStrategyRead[]>({
    queryKey: ['search-strategies', projectId],
    queryFn: () => searchStrategiesApi.list(projectId as string),
    enabled: !!projectId,
  })
}

export function useCreateSearchStrategy(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: SearchStrategyCreate) =>
      searchStrategiesApi.create(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['search-strategies', projectId] })
    },
  })
}

export function useUpdateSearchStrategy(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: SearchStrategyUpdate }) =>
      searchStrategiesApi.update(projectId, id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['search-strategies', projectId] })
    },
  })
}

export function useDeleteSearchStrategy(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => searchStrategiesApi.remove(projectId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['search-strategies', projectId] })
    },
  })
}

export function useTranslateSearchStrategy(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      to,
      persist,
    }: {
      id: string
      to: TranslationTarget
      persist?: boolean
    }) => searchStrategiesApi.translate(projectId, id, to, persist ?? false),
    onSuccess: (_data, vars) => {
      if (vars.persist) {
        qc.invalidateQueries({ queryKey: ['search-strategies', projectId] })
      }
    },
  })
}
