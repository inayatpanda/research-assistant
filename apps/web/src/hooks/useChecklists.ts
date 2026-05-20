import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  checklistsApi,
  type ChecklistCatalogueRead,
  type ChecklistCatalogueSummary,
  type ChecklistRunItemPatch,
  type ChecklistRunRead,
  type ChecklistRunSummary,
} from '@/lib/api'

export function useChecklistCatalogue() {
  return useQuery<ChecklistCatalogueSummary[]>({
    queryKey: ['checklists', 'catalogue'],
    queryFn: () => checklistsApi.listCatalogue(),
    staleTime: 5 * 60_000,
  })
}

export function useChecklistCatalogueDetail(key: string | null) {
  return useQuery<ChecklistCatalogueRead>({
    queryKey: ['checklists', 'catalogue', key],
    queryFn: () => checklistsApi.getCatalogue(key as string),
    enabled: !!key,
    staleTime: 5 * 60_000,
  })
}

export function useChecklistRuns(projectId: string | null) {
  return useQuery<ChecklistRunSummary[]>({
    queryKey: ['checklists', 'runs', projectId],
    queryFn: () => checklistsApi.listRuns(projectId as string),
    enabled: !!projectId,
  })
}

export function useChecklistRun(projectId: string | null, runId: string | null) {
  return useQuery<ChecklistRunRead>({
    queryKey: ['checklists', 'run', projectId, runId],
    queryFn: () =>
      checklistsApi.getRun(projectId as string, runId as string),
    enabled: !!projectId && !!runId,
  })
}

export function useCreateChecklistRun(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { checklist_key: string; title: string }) =>
      checklistsApi.createRun(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['checklists', 'runs', projectId] })
    },
  })
}

export function usePatchChecklistItem(projectId: string, runId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (args: { itemId: string; patch: ChecklistRunItemPatch }) =>
      checklistsApi.patchItem(projectId, runId, args.itemId, args.patch),
    onSuccess: (run) => {
      qc.setQueryData(['checklists', 'run', projectId, runId], run)
      qc.invalidateQueries({ queryKey: ['checklists', 'runs', projectId] })
    },
  })
}

export function useAutoCheckRun(projectId: string, runId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => checklistsApi.autoCheck(projectId, runId),
    onSuccess: (run) => {
      qc.setQueryData(['checklists', 'run', projectId, runId], run)
      qc.invalidateQueries({ queryKey: ['checklists', 'runs', projectId] })
    },
  })
}

export function useDeleteChecklistRun(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (runId: string) =>
      checklistsApi.deleteRun(projectId, runId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['checklists', 'runs', projectId] })
    },
  })
}
