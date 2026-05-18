import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  snapshotsApi,
  type SnapshotCreate,
  type SnapshotDiffResponse,
  type SnapshotRead,
  type SnapshotSummary,
} from '@/lib/api'

export function useSnapshots(projectId: string | null) {
  return useQuery<SnapshotSummary[]>({
    queryKey: ['snapshots', projectId],
    queryFn: () => snapshotsApi.list(projectId as string),
    enabled: !!projectId,
  })
}

export function useSnapshot(
  projectId: string | null,
  snapshotId: string | null,
) {
  return useQuery<SnapshotRead>({
    queryKey: ['snapshot', projectId, snapshotId],
    queryFn: () =>
      snapshotsApi.get(projectId as string, snapshotId as string),
    enabled: !!projectId && !!snapshotId,
  })
}

export function useCreateSnapshot(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: SnapshotCreate) => snapshotsApi.create(projectId, body),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['snapshots', projectId] }),
  })
}

export function useDeleteSnapshot(projectId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (snapshotId: string) =>
      snapshotsApi.delete(projectId, snapshotId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['snapshots', projectId] }),
  })
}

/** Fetch a diff between a base snapshot and an optional target snapshot.
 *  Pass `targetId=null` to diff against current live project state. */
export function useSnapshotDiff(
  projectId: string | null,
  baseId: string | null,
  targetId: string | null,
) {
  return useQuery<SnapshotDiffResponse>({
    queryKey: ['snapshot-diff', projectId, baseId, targetId ?? 'current'],
    queryFn: () =>
      snapshotsApi.diff(
        projectId as string,
        baseId as string,
        targetId ?? undefined,
      ),
    enabled: !!projectId && !!baseId,
  })
}
