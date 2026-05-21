import { useNavigate, useParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import {
  useAcceptInvitation,
  useCurrentUser,
  useInvitationLanding,
} from '@/hooks/useAuth'

export default function InvitePage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const { data: user, isLoading: userLoading } = useCurrentUser()
  const { data: landing, isLoading, error } = useInvitationLanding(token ?? null)
  const accept = useAcceptInvitation()

  if (isLoading || userLoading) {
    return <div className="px-4 py-8 text-sm text-muted-foreground">Loading…</div>
  }
  if (error || !landing) {
    return (
      <div className="px-4 py-8">
        <h1 className="text-xl font-semibold">Invitation unavailable</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          This invitation may have been revoked or expired.
        </p>
      </div>
    )
  }

  async function onAccept() {
    if (!token) return
    await accept.mutateAsync(token)
    navigate(`/projects/${landing!.project_id}`, { replace: true })
  }

  return (
    <div className="container mx-auto max-w-xl px-4 py-12">
      <h1 className="text-2xl font-semibold">You're invited</h1>
      <p className="mt-4 text-sm">
        <span className="font-medium">{landing.inviter_display_name}</span> has
        invited you to join{' '}
        <span className="font-medium">{landing.project_title}</span> as a{' '}
        <span className="font-medium">{landing.role}</span>.
      </p>
      <div className="mt-6 flex gap-3">
        {user ? (
          <Button onClick={onAccept} disabled={accept.isPending}>
            Accept invitation
          </Button>
        ) : (
          <>
            <Button
              onClick={() =>
                navigate('/signup', { state: { from: `/invite/${token}` } })
              }
            >
              Create account
            </Button>
            <Button
              variant="outline"
              onClick={() =>
                navigate('/login', { state: { from: `/invite/${token}` } })
              }
            >
              Sign in
            </Button>
          </>
        )}
      </div>
    </div>
  )
}
