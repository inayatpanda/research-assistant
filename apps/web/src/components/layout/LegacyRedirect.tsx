/**
 * MP12.5 — back-compat redirect for the pre-URL-scoped routes.
 *
 * Before MP12.5 the module pages lived at `/library`, `/manuscript`,
 * etc. and read the active projectId from Zustand. Old bookmarks,
 * toast actions, and email links still point at those paths. Each
 * legacy path now mounts this component, which looks up the
 * "last viewed" project and forwards to the equivalent URL-scoped
 * route (e.g. `/library` → `/projects/<id>/library`).
 *
 * If no last-viewed projectId is recorded the user lands on `/` to
 * pick one. These legacy routes will be removed in MP14.
 */
import { Navigate, useLocation, useParams } from 'react-router-dom'

import { useLastViewedProject } from '@/lib/projectContext'

export function LegacyRedirect({ to }: { to: string }) {
  const projectId = useLastViewedProject((s) => s.projectId)
  const { search, hash } = useLocation()

  // Preserve query string + hash so deep links like
  // `/manuscript?section=Results` still land in the right place.
  const suffix = `${search}${hash}`

  if (!projectId) return <Navigate to="/" replace />
  return <Navigate to={`/projects/${projectId}${to}${suffix}`} replace />
}

/**
 * Specialised redirect for `/reader/:articleId` — preserves the article
 * id when forwarding to the URL-scoped route.
 */
export function ReaderLegacyForward() {
  const projectId = useLastViewedProject((s) => s.projectId)
  const { articleId } = useParams<{ articleId: string }>()
  const { search, hash } = useLocation()
  const suffix = `${search}${hash}`
  if (!projectId) return <Navigate to="/" replace />
  return (
    <Navigate
      to={`/projects/${projectId}/reader/${articleId ?? ''}${suffix}`}
      replace
    />
  )
}
