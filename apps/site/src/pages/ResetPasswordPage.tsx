/**
 * Phase L1c.5 — Reset password page.
 *
 * Reads the reset token from the URL params, POSTs to /api/reset-password
 * with the new password, then redirects to /login on success.
 */
import { type FormEvent, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AlertCircle, Loader2, Lock } from 'lucide-react'
import { humaniseError, licenseApi } from '@/lib/licenseApi'
import {
  PASSWORD_HINT,
  PASSWORD_MIN_LENGTH,
  PASSWORD_PATTERN,
  isStrongPassword,
} from '@/lib/passwordRules'

export default function ResetPasswordPage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    if (!token) {
      setError('Missing reset token. Request a new reset link.')
      return
    }
    if (!isStrongPassword(password)) {
      setError(
        `Password must be at least ${PASSWORD_MIN_LENGTH} characters and include a digit.`,
      )
      return
    }
    if (password !== confirm) {
      setError("Passwords don't match.")
      return
    }
    setSubmitting(true)
    try {
      await licenseApi.resetPassword({ token, new_password: password })
      navigate('/login')
    } catch (err) {
      setError(humaniseError(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="py-16 sm:py-20">
      <div className="container-narrow max-w-md">
        <header className="text-center">
          <span className="badge-soft">Reset</span>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
            Set a new password
          </h1>
          <p className="mt-3 text-sm text-ink-muted">{PASSWORD_HINT}</p>
        </header>

        <form
          onSubmit={handleSubmit}
          className="mt-8 space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
        >
          <div>
            <label
              htmlFor="reset-password"
              className="block text-sm font-medium text-ink"
            >
              New password
            </label>
            <input
              id="reset-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={PASSWORD_MIN_LENGTH}
              pattern={PASSWORD_PATTERN}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          <div>
            <label
              htmlFor="reset-confirm"
              className="block text-sm font-medium text-ink"
            >
              Confirm new password
            </label>
            <input
              id="reset-confirm"
              type="password"
              autoComplete="new-password"
              required
              minLength={PASSWORD_MIN_LENGTH}
              pattern={PASSWORD_PATTERN}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          {error ? (
            <div
              role="alert"
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
          >
            {submitting ? (
              <>
                <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
                Updating…
              </>
            ) : (
              <>
                <Lock aria-hidden className="h-4 w-4" />
                Set new password
              </>
            )}
          </button>

          <p className="text-center text-xs text-ink-muted">
            <Link to="/login" className="link-soft">
              Back to sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
