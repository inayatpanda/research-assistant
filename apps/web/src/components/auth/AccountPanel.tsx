import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  useChangePassword,
  useCurrentUser,
  useLogout,
  useRevokeSession,
  useSessions,
} from '@/hooks/useAuth'

export function AccountPanel() {
  const { data: user } = useCurrentUser()
  const { data: sessions } = useSessions()
  const change = useChangePassword()
  const revoke = useRevokeSession()
  const logout = useLogout()
  const navigate = useNavigate()
  const [oldPw, setOldPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [ok, setOk] = useState(false)

  async function onChangePassword(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setOk(false)
    if (newPw.length < 10 || !/\d/.test(newPw)) {
      setError('New password must be at least 10 characters and include a digit.')
      return
    }
    try {
      await change.mutateAsync({ old_password: oldPw, new_password: newPw })
      setOldPw('')
      setNewPw('')
      setOk(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update password.')
    }
  }

  async function onLogout() {
    await logout.mutateAsync()
    navigate('/login', { replace: true })
  }

  if (!user) {
    return null
  }

  return (
    <div data-testid="account-panel" className="space-y-6">
      <section className="rounded-md border bg-card p-4">
        <h2 className="text-lg font-semibold">Profile</h2>
        <dl className="mt-2 grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-muted-foreground">Email</dt>
          <dd>{user.email}</dd>
          <dt className="text-muted-foreground">Display name</dt>
          <dd>{user.display_name}</dd>
        </dl>
        <Button
          variant="outline"
          className="mt-4"
          onClick={onLogout}
          data-testid="account-logout"
        >
          Log out
        </Button>
      </section>

      <section className="rounded-md border bg-card p-4">
        <h2 className="text-lg font-semibold">Change password</h2>
        <form onSubmit={onChangePassword} className="mt-3 grid gap-3">
          <div className="grid gap-2">
            <Label htmlFor="old-pw">Current password</Label>
            <Input
              id="old-pw"
              type="password"
              autoComplete="current-password"
              value={oldPw}
              onChange={(e) => setOldPw(e.target.value)}
              required
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="new-pw">New password</Label>
            <Input
              id="new-pw"
              type="password"
              autoComplete="new-password"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              required
            />
          </div>
          {error ? (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          ) : null}
          {ok ? (
            <p className="text-sm text-emerald-600">Password updated.</p>
          ) : null}
          <Button type="submit" disabled={change.isPending}>
            Update password
          </Button>
        </form>
      </section>

      <section className="rounded-md border bg-card p-4">
        <h2 className="text-lg font-semibold">Active sessions</h2>
        <ul className="mt-3 divide-y" data-testid="account-sessions">
          {(sessions ?? []).map((s) => (
            <li
              key={s.id}
              className="flex items-center justify-between gap-3 py-2 text-sm"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate font-mono text-xs">{s.id}</p>
                <p className="text-muted-foreground">
                  {s.user_agent ?? '(no user-agent)'} · last seen{' '}
                  {new Date(s.last_seen_at).toLocaleString()}
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => revoke.mutate(s.id)}
              >
                Revoke
              </Button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

export default AccountPanel
