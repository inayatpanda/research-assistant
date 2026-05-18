import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { figuresApi, type Figure } from '@/lib/api'

export function useFigures(projectId: string | null) {
  return useQuery<Figure[]>({
    queryKey: ['figures', projectId],
    queryFn: () => figuresApi.list(projectId as string),
    enabled: !!projectId,
  })
}

/** Convenience hook used by the TipTap Figure node-view to render the bound image. */
export function useFigure(figureId: string): Figure | undefined {
  const q = useQuery<Figure>({
    queryKey: ['figure', figureId],
    queryFn: () => figuresApi.get(figureId),
    enabled: !!figureId,
  })
  return q.data
}

export function useUploadFigure(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => figuresApi.upload(projectId, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['figures', projectId] }),
  })
}

export function useUpdateFigure(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: { caption?: string; alt_text?: string } }) =>
      figuresApi.patch(id, body),
    onSuccess: (fig) => {
      qc.invalidateQueries({ queryKey: ['figures', projectId] })
      qc.invalidateQueries({ queryKey: ['figure', fig.id] })
    },
  })
}

export function useReorderFigures(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (orderedIds: string[]) => figuresApi.reorder(projectId, orderedIds),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['figures', projectId] }),
  })
}

export function useDeleteFigure(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => figuresApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['figures', projectId] }),
  })
}
