/**
 * MP12.5 — guards every `/projects/:projectId/*` route.
 *
 * Responsibilities:
 *  - Resolve `projectId` from the URL.
 *  - Fetch the Project object via `projectsApi.get(projectId)`.
 *  - On 404, redirect to `/` with a toast.
 *  - Provide the projectId (and resolved Project) to descendants through
 *    `ProjectContext` so `useProjectId()` / `useProject()` work.
 *  - Record this projectId as the user's "last viewed" project so the
 *    next blank tab knows which project to default to.
 *
 * The guard renders its `<Outlet />` immediately with `project = null`
 * while the query is in flight; pages already tolerate `project?.title`
 * being `undefined`, so we don't gate the render on a loading spinner.
 */
import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo } from 'react'
import { Navigate, Outlet, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { projectsApi } from '@/lib/api'
import {
  ProjectContext,
  type ProjectContextValue,
  useLastViewedProject,
} from '@/lib/projectContext'

export function ProjectLayoutGuard() {
  const { projectId } = useParams<{ projectId: string }>()
  const setLastViewed = useLastViewedProject((s) => s.set)

  const { data: project, isError, error, isFetching } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
    retry: false,
  })

  // Record "last viewed" as soon as we have a valid projectId. We do this
  // even before the project fetch resolves — if the URL is valid, the
  // intent to view it is enough for new-tab defaulting.
  useEffect(() => {
    if (projectId) setLastViewed(projectId)
  }, [projectId, setLastViewed])

  // Surface a single toast on 404 (or any fetch failure) before redirecting.
  useEffect(() => {
    if (isError) {
      const msg = error instanceof Error ? error.message : ''
      // Treat both 404 and other failures as "not found" for routing purposes;
      // the toast carries the underlying server message when present.
      toast.error(msg ? `Project not found: ${msg}` : 'Project not found')
    }
  }, [isError, error])

  const ctxValue = useMemo<ProjectContextValue | null>(
    () => (projectId ? { projectId, project: project ?? null } : null),
    [projectId, project],
  )

  if (!projectId) return <Navigate to="/" replace />
  if (isError) return <Navigate to="/" replace />

  // `isFetching` is intentionally ignored — we render the child route
  // straight away with `project: null` so the page can show its own
  // skeleton via the same query (it'll dedupe on the same key).
  void isFetching

  return (
    <ProjectContext.Provider value={ctxValue}>
      <Outlet />
    </ProjectContext.Provider>
  )
}
