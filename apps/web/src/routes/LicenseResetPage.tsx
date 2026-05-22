/**
 * Phase L1b — Password reset completion.
 *
 * Reads ``:token`` from the URL (the email link), accepts a new
 * password, calls the worker, then redirects to /license with a
 * success banner.
 */
import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { LicenseError, licenseApi } from '@/lib/licenseApi'

export default function LicenseResetPage() {
  const navigate = useNavigate()
  const { token = '' } = useParams<{ token: string }>()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (password.length < 10 || !/\d/.test(password)) {
      setError('Password must be at least 10 characters and include a digit.')
      return
    }
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setBusy(true)
    try {
      await licenseApi.resetPassword({ token, new_password: password })
      navigate('/license', {
        replace: true,
        state: {
          banner: 'Password updated. Please sign in again.',
        },
      })
    } catch (err) {
      if (err instanceof LicenseError) {
        if (err.code === 'invalid_token' || err.status === 401) {
          setError('This reset link is invalid or has expired.')
        } else if (err.code === 'network_error') {
          setError('Could not reach the licence server.')
        } else {
          setError(err.message || err.code)
        }
      } else {
        setError('Something went wrong. Try again.')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 px-4 py-10">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Choose a new password</CardTitle>
          <CardDescription>At least 10 characters with one digit.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={submit} className="space-y-3">
            <div>
              <Label htmlFor="password">New password</Label>
              <Input
                id="password"
                data-testid="reset-input-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>
            <div>
              <Label htmlFor="confirm">Confirm new password</Label>
              <Input
                id="confirm"
                data-testid="reset-input-confirm"
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                autoComplete="new-password"
              />
            </div>
            {error && (
              <div
                data-testid="reset-error"
                className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-[12px] text-rose-900"
              >
                {error}
              </div>
            )}
            <Button
              type="submit"
              disabled={busy}
              data-testid="reset-submit"
              className="w-full"
            >
              {busy ? 'Updating…' : 'Set new password'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
