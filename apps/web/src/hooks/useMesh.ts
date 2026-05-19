import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  meshApi,
  type MeshSearchResponse,
  type MeshTermCreate,
  type MeshTermRead,
} from '@/lib/api'

export function useMeshCache(projectId: string | null) {
  return useQuery<MeshTermRead[]>({
    queryKey: ['mesh-cache', projectId],
    queryFn: () => meshApi.listCache(projectId as string),
    enabled: !!projectId,
  })
}

export function useMeshSearch(
  projectId: string | null,
  query: string,
  enabled = true,
) {
  return useQuery<MeshSearchResponse>({
    queryKey: ['mesh-search', projectId, query],
    queryFn: () => meshApi.search(projectId as string, query),
    enabled: !!projectId && !!query.trim() && enabled,
    staleTime: 5 * 60_000,
  })
}

export function useUpsertMesh(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: MeshTermCreate) => meshApi.upsertCache(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mesh-cache', projectId] })
    },
  })
}

export function useDeleteMesh(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (meshId: string) => meshApi.deleteCache(projectId, meshId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mesh-cache', projectId] })
    },
  })
}

export function useSuggestMesh(projectId: string) {
  return useMutation({
    mutationFn: (pico: Record<string, string | undefined>) =>
      meshApi.suggest(projectId, pico as any),
  })
}
