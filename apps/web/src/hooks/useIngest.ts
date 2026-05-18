/**
 * Phase 8.6 — TanStack hooks for the ingest surfaces.
 *
 * On any successful import or merge, invalidates the project's article
 * list AND the duplicates feed so the UI re-renders with the rewired rows.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  ingestApi,
  type ArticleMetadata,
  type PubMedSearchFilters,
} from '@/lib/api'

export function useLookupDoi(projectId: string) {
  return useMutation({
    mutationFn: (doi: string) => ingestApi.lookupDoi(projectId, doi),
  })
}

export function useSearchPubMed(projectId: string) {
  return useMutation({
    mutationFn: ({
      query,
      retmax,
      sort,
      filters,
    }: {
      query: string
      retmax?: number
      sort?: 'relevance' | 'date'
      filters?: PubMedSearchFilters
    }) => ingestApi.searchPubMed(projectId, query, retmax, { sort, filters }),
  })
}

export function useImportFromMetadata(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (items: ArticleMetadata[]) =>
      ingestApi.importFromMetadata(projectId, items),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['articles', projectId] })
      qc.invalidateQueries({ queryKey: ['duplicates', projectId] })
    },
  })
}

export function useImportRis(projectId: string) {
  return useMutation({
    mutationFn: (file: File) => ingestApi.importRis(projectId, file),
  })
}

export function useImportBibtex(projectId: string) {
  return useMutation({
    mutationFn: (file: File) => ingestApi.importBibtex(projectId, file),
  })
}

export function useDuplicates(projectId: string | undefined) {
  return useQuery({
    queryKey: ['duplicates', projectId],
    queryFn: () => ingestApi.duplicates(projectId!),
    enabled: !!projectId,
  })
}

export function useMergeDuplicates(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      keepId,
      dropIds,
    }: {
      keepId: string
      dropIds: string[]
    }) => ingestApi.merge(projectId, keepId, dropIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['articles', projectId] })
      qc.invalidateQueries({ queryKey: ['duplicates', projectId] })
    },
  })
}
