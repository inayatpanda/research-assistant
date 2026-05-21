import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useCurrentUser } from '@/hooks/useAuth'

/**
 * Wraps a subtree that requires authentication. While the ``/me`` query
 * is still pending we render a transparent placeholder. On 401 we
 * redirect to ``/login`` and preserve the attempted URL via the
 * router state so the post-login redirect can return the user there.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { data: user, isLoading } = useCurrentUser()
  const location = useLocation()
  if (isLoading) {
    return (
      <div className="flex h-full w-full items-center justify-center text-sm text-muted-foreground">
        Loading…
      </div>
    )
  }
  if (!user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search }}
      />
    )
  }
  return <>{children}</>
}

export default RequireAuth
