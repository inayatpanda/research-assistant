import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  metaAnalysisApi,
  type MetaAnalysisCreate,
  type MetaAnalysisUpdate,
  type MetaInputCreate,
} from '@/lib/api'

export function useMetaList(projectId: string | undefined) {
  return useQuery({
    queryKey: ['meta', projectId],
    queryFn: () => metaAnalysisApi.list(projectId!),
    enabled: !!projectId,
  })
}

export function useMetaDetail(projectId: string | undefined, metaId: string | undefined) {
  return useQuery({
    queryKey: ['meta', projectId, metaId],
    queryFn: () => metaAnalysisApi.get(projectId!, metaId!),
    enabled: !!projectId && !!metaId,
  })
}

export function useCreateMeta(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: MetaAnalysisCreate) => metaAnalysisApi.create(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['meta', projectId] })
    },
  })
}

export function usePatchMeta(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ metaId, body }: { metaId: string; body: MetaAnalysisUpdate }) =>
      metaAnalysisApi.patch(projectId, metaId, body),
    onSuccess: (_data, { metaId }) => {
      qc.invalidateQueries({ queryKey: ['meta', projectId] })
      qc.invalidateQueries({ queryKey: ['meta', projectId, metaId] })
    },
  })
}

export function useDeleteMeta(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (metaId: string) => metaAnalysisApi.remove(projectId, metaId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['meta', projectId] })
    },
  })
}

export function useRunMeta(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (metaId: string) => metaAnalysisApi.run(projectId, metaId),
    onSuccess: (_data, metaId) => {
      qc.invalidateQueries({ queryKey: ['meta', projectId] })
      qc.invalidateQueries({ queryKey: ['meta', projectId, metaId] })
    },
  })
}

export function useInterpretMeta(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (metaId: string) => metaAnalysisApi.interpret(projectId, metaId),
    onSuccess: (_data, metaId) => {
      // Refresh both the list and the per-meta detail so any consumer of
      // either query (list panel + detail page) sees the new
      // `ai_interpretation`.  Without the list refresh users saw the
      // "Interpreting…" pending state until a hard reload.
      qc.invalidateQueries({ queryKey: ['meta', projectId] })
      qc.invalidateQueries({ queryKey: ['meta', projectId, metaId] })
    },
  })
}

export function usePushMeta(projectId: string) {
  return useMutation({
    mutationFn: (metaId: string) => metaAnalysisApi.push(projectId, metaId),
  })
}

export function useUpsertMetaInput(projectId: string, metaId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: MetaInputCreate) =>
      metaAnalysisApi.upsertInput(projectId, metaId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['meta', projectId, metaId] })
    },
  })
}
