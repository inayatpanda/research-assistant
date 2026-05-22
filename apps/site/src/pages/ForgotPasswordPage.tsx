/**
 * Phase L1c.5 — Forgot password page.
 *
 * POSTs the email to /api/forgot-password and shows a generic
 * "check your email" confirmation regardless of whether the address
 * exists in our database — to avoid leaking which emails are accounts.
 */
import { type FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { Mail, Loader2, CheckCircle2 } from 'lucide-react'
import { licenseApi } from '@/lib/licenseApi'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setSubmitting(true)
    try {
      await licenseApi.forgotPassword(email.trim())
    } catch {
      /* swallow — we always show the same confirmation */
    } finally {
      setSubmitting(false)
      setSubmitted(true)
    }
  }

  if (submitted) {
    return (
      <div className="py-16 sm:py-20">
        <div className="container-narrow max-w-md">
          <div
            data-testid="forgot-submitted"
            className="rounded-2xl border border-emerald-200 bg-emerald-50 p-8 text-center"
          >
            <CheckCircle2
              aria-hidden
              className="mx-auto h-12 w-12 text-emerald-600"
            />
            <h1 className="mt-4 text-2xl font-semibold tracking-tight text-ink">
              Check your email
            </h1>
            <p className="mt-2 text-sm text-ink-muted">
              If an account exists for that email, we&rsquo;ve sent password
              reset instructions. The link expires in 1 hour.
            </p>
            <Link to="/login" className="btn-secondary mt-6">
              Back to sign in
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="py-16 sm:py-20">
      <div className="container-narrow max-w-md">
        <header className="text-center">
          <span className="badge-soft">Reset</span>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
            Forgot your password?
          </h1>
          <p className="mt-3 text-sm text-ink-muted">
            Enter the email you used to sign up and we&rsquo;ll send a reset
            link.
          </p>
        </header>

        <form
          onSubmit={handleSubmit}
          className="mt-8 space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
        >
          <div>
            <label
              htmlFor="forgot-email"
              className="block text-sm font-medium text-ink"
            >
              Email
            </label>
            <input
              id="forgot-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="you@example.com"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? (
              <>
                <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
                Sending…
              </>
            ) : (
              <>
                <Mail aria-hidden className="h-4 w-4" />
                Send reset link
              </>
            )}
          </button>

          <p className="text-center text-xs text-ink-muted">
            Remembered it?{' '}
            <Link to="/login" className="link-soft">
              Back to sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
