import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  narrativeSynthesisApi,
  type NarrativeSynthesisCreate,
  type NarrativeSynthesisRead,
  type NarrativeSynthesisUpdate,
} from '@/lib/api'

export function useNarrativeSynthesis(projectId: string | null) {
  return useQuery<NarrativeSynthesisRead[]>({
    queryKey: ['narrative-synthesis', projectId],
    queryFn: () => narrativeSynthesisApi.list(projectId as string),
    enabled: !!projectId,
  })
}

export function useCreateNarrativeEntry(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: NarrativeSynthesisCreate) =>
      narrativeSynthesisApi.create(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['narrative-synthesis', projectId] })
    },
  })
}

export function useUpdateNarrativeEntry(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: NarrativeSynthesisUpdate }) =>
      narrativeSynthesisApi.update(projectId, id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['narrative-synthesis', projectId] })
    },
  })
}

export function useDeleteNarrativeEntry(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => narrativeSynthesisApi.remove(projectId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['narrative-synthesis', projectId] })
    },
  })
}

export function usePushNarrative(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => narrativeSynthesisApi.push(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['manuscript', projectId] })
    },
  })
}
