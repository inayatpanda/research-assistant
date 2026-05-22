/**
 * Phase L1c.3 — Login page.
 *
 * On success, redirects to /account. The 409 device_limit_exceeded case
 * is handled with the simpler messaging route per the L1c spec: rather
 * than implementing device-revoke UX on the marketing site (which would
 * require an authenticated request before the user is signed in
 * anywhere), we direct them to revoke a slot from the desktop app's
 * Settings → License → Manage devices screen.
 */
import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AlertCircle, Loader2, ArrowRight } from 'lucide-react'
import {
  DEVICE_LIMIT,
  LicenseError,
  humaniseError,
  licenseApi,
  saveSessionToken,
} from '@/lib/licenseApi'

export default function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deviceLimitHit, setDeviceLimitHit] = useState(false)

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setDeviceLimitHit(false)
    setSubmitting(true)
    try {
      const res = await licenseApi.login({
        email: email.trim(),
        password,
      })
      saveSessionToken(res.token)
      navigate('/account')
    } catch (err) {
      if (err instanceof LicenseError && err.code === 'device_limit_exceeded') {
        setDeviceLimitHit(true)
        setError(null)
      } else {
        const friendly =
          err instanceof LicenseError && err.code === 'network_error'
            ? "Can't reach the server. Please try again."
            : humaniseError(err)
        setError(friendly)
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="py-16 sm:py-20">
      <div className="container-narrow max-w-md">
        <header className="text-center">
          <span className="badge-soft">Sign in</span>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
            Welcome back
          </h1>
          <p className="mt-3 text-sm text-ink-muted">
            Sign in to manage your licence and devices.
          </p>
        </header>

        <form
          onSubmit={handleSubmit}
          data-testid="login-form"
          className="mt-8 space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
          noValidate
        >
          <div>
            <label
              htmlFor="login-email"
              className="block text-sm font-medium text-ink"
            >
              Email
            </label>
            <input
              id="login-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <div className="flex items-center justify-between">
              <label
                htmlFor="login-password"
                className="block text-sm font-medium text-ink"
              >
                Password
              </label>
              <Link
                to="/forgot-password"
                className="text-xs text-accent hover:underline"
              >
                Forgot password?
              </Link>
            </div>
            <input
              id="login-password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          {deviceLimitHit ? (
            <div
              role="alert"
              data-testid="login-device-limit"
              className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
            >
              <p className="font-semibold">
                You&rsquo;re signed in on {DEVICE_LIMIT} devices already.
              </p>
              <p className="mt-1 text-xs">
                Sign in on one of your existing devices and use{' '}
                <strong>Settings → License → Manage devices</strong> in the
                app to free a slot. Then try logging in here again.
              </p>
            </div>
          ) : null}

          {error ? (
            <div
              role="alert"
              data-testid="login-error"
              className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900"
            >
              <AlertCircle aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : null}

          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60"
            data-testid="login-submit"
          >
            {submitting ? (
              <>
                <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
                Signing in…
              </>
            ) : (
              <>
                Sign in
                <ArrowRight aria-hidden className="h-4 w-4" />
              </>
            )}
          </button>

          <p className="text-center text-xs text-ink-muted">
            Don&rsquo;t have an account?{' '}
            <Link to="/signup" className="link-soft">
              Start a free trial
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
