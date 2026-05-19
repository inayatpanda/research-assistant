import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  outcomeInstrumentsApi,
  type OutcomeInstrumentCreate,
  type OutcomeInstrumentRead,
  type OutcomeInstrumentUpdate,
} from '@/lib/api'

export function useOutcomeInstruments(projectId: string | null) {
  return useQuery<OutcomeInstrumentRead[]>({
    queryKey: ['outcome-instruments', projectId],
    queryFn: () => outcomeInstrumentsApi.list(projectId as string),
    enabled: !!projectId,
  })
}

export function useCreateOutcomeInstrument(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: OutcomeInstrumentCreate) =>
      outcomeInstrumentsApi.create(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outcome-instruments', projectId] })
    },
  })
}

export function useUpdateOutcomeInstrument(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: OutcomeInstrumentUpdate }) =>
      outcomeInstrumentsApi.update(projectId, id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outcome-instruments', projectId] })
    },
  })
}

export function useDeleteOutcomeInstrument(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => outcomeInstrumentsApi.remove(projectId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['outcome-instruments', projectId] })
    },
  })
}

export function usePushOutcomeInstruments(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => outcomeInstrumentsApi.push(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['manuscript', projectId] })
    },
  })
}
