import { useMutation, useQuery } from '@tanstack/react-query'

import { metaExtensionsApi } from '@/lib/api'

export function usePublicationBias(
  projectId: string,
  metaId: string | null,
  enabled = true,
) {
  return useQuery({
    queryKey: ['meta-publication-bias', projectId, metaId],
    queryFn: () => metaExtensionsApi.publicationBias(projectId, metaId as string),
    enabled: !!metaId && enabled,
  })
}

export function useLeaveOneOut(
  projectId: string,
  metaId: string | null,
  enabled = true,
) {
  return useQuery({
    queryKey: ['meta-leave-one-out', projectId, metaId],
    queryFn: () => metaExtensionsApi.leaveOneOut(projectId, metaId as string),
    enabled: !!metaId && enabled,
  })
}

export function useSubgroupInteraction(
  projectId: string,
  metaId: string | null,
  enabled = true,
) {
  return useQuery({
    queryKey: ['meta-subgroup-interaction', projectId, metaId],
    queryFn: () =>
      metaExtensionsApi.subgroupInteraction(projectId, metaId as string),
    enabled: !!metaId && enabled,
    retry: false,
  })
}

export function useMetaRegression(projectId: string) {
  return useMutation({
    mutationFn: ({
      metaId,
      moderator,
      moderator_label,
    }: {
      metaId: string
      moderator: number[]
      moderator_label?: string
    }) =>
      metaExtensionsApi.metaRegression(
        projectId,
        metaId,
        moderator,
        moderator_label,
      ),
  })
}
