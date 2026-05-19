import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  gradeApi,
  type GradeAssessmentCreate,
  type GradeAssessmentRead,
} from '@/lib/api'

export function useGradeList(projectId: string | null) {
  return useQuery<GradeAssessmentRead[]>({
    queryKey: ['grade', projectId],
    queryFn: () => gradeApi.list(projectId as string),
    enabled: !!projectId,
  })
}

export function useUpsertGrade(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: GradeAssessmentCreate) =>
      gradeApi.upsert(projectId, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['grade', projectId] })
    },
  })
}

export function useDeleteGrade(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (gradeId: string) => gradeApi.remove(projectId, gradeId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['grade', projectId] })
    },
  })
}

export function usePushGrade(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => gradeApi.push(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['manuscript', projectId] })
    },
  })
}
