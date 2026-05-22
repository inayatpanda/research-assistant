/**
 * Phase L1b — Forgot-password landing.
 *
 * Submits the email to the worker's /api/forgot-password endpoint and
 * shows a success message regardless (the worker always returns 200 to
 * avoid leaking which addresses are registered).
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'

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

export default function LicenseForgotPage() {
  const [email, setEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await licenseApi.forgotPassword(email)
      setSent(true)
    } catch (err) {
      setError(
        err instanceof LicenseError && err.code === 'network_error'
          ? 'Could not reach the licence server.'
          : 'Something went wrong. Try again in a minute.',
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 px-4 py-10">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Reset your password</CardTitle>
          <CardDescription>
            We&apos;ll email you a one-time link to reset your password.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {sent ? (
            <div
              data-testid="forgot-sent"
              className="rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-[13px] text-emerald-900"
            >
              If an account exists for <strong>{email}</strong>, you&apos;ll
              receive a reset link shortly. Check your inbox (and spam folder).
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-3">
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  data-testid="forgot-input-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>
              {error && (
                <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-[12px] text-rose-900">
                  {error}
                </div>
              )}
              <Button
                type="submit"
                disabled={busy}
                data-testid="forgot-submit"
                className="w-full"
              >
                {busy ? 'Sending…' : 'Send reset link'}
              </Button>
            </form>
          )}
          <Link
            to="/license"
            className="text-[12px] text-muted-foreground hover:text-foreground hover:underline"
          >
            Back to sign in
          </Link>
        </CardContent>
      </Card>
    </div>
  )
}
