/**
 * Phase L1c.2 — Signup page.
 *
 * POSTs to the L1a worker's /api/signup. On success we save the session
 * token + the trial token (so the user's browser can later paste them
 * into the app's licence screen) and show a confirmation panel with the
 * expiry date and a big "Download for your OS" CTA.
 */
import { type FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  CheckCircle2,
  AlertCircle,
  Loader2,
  Download,
  ArrowRight,
} from 'lucide-react'
import {
  LicenseError,
  TRIAL_DAYS,
  humaniseError,
  licenseApi,
  saveSessionToken,
  saveTrialToken,
  type LicenseAccount,
} from '@/lib/licenseApi'
import {
  PASSWORD_HINT,
  PASSWORD_MIN_LENGTH,
  PASSWORD_PATTERN,
  isStrongPassword,
} from '@/lib/passwordRules'

interface SuccessState {
  account: LicenseAccount
}

export default function SignupPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [acceptedTerms, setAcceptedTerms] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<SuccessState | null>(null)

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    if (!acceptedTerms) {
      setError('Please accept the terms before continuing.')
      return
    }
    if (!isStrongPassword(password)) {
      // Match the server's validator exactly so the user doesn't
      // round-trip a 400 only to get the same message back. (Fix-13/13)
      setError(
        `Password must be at least ${PASSWORD_MIN_LENGTH} characters and include a digit.`,
      )
      return
    }
    setSubmitting(true)
    try {
      const res = await licenseApi.signup({
        email: email.trim(),
        password,
        display_name: displayName.trim(),
      })
      saveSessionToken(res.token)
      saveTrialToken(res.token)
      setSuccess({ account: res.account })
    } catch (err) {
      const friendly =
        err instanceof LicenseError && err.code === 'network_error'
          ? "Can't reach the server. Please try again."
          : humaniseError(err)
      setError(friendly)
    } finally {
      setSubmitting(false)
    }
  }

  if (success) {
    return <SignupSuccess account={success.account} />
  }

  return (
    <div className="py-16 sm:py-20">
      <div className="container-narrow max-w-md">
        <header className="text-center">
          <span className="badge-soft">Sign up</span>
          <h1 className="mt-4 text-3xl font-semibold tracking-tight sm:text-4xl">
            Start your {TRIAL_DAYS}-day free trial
          </h1>
          <p className="mt-3 text-sm text-ink-muted">
            No credit card required. Cancel anytime — the app keeps working
            on your laptop after the trial ends, just with paid modules locked.
          </p>
        </header>

        <form
          onSubmit={handleSubmit}
          data-testid="signup-form"
          className="mt-8 space-y-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-card"
          noValidate
        >
          <div>
            <label
              htmlFor="signup-name"
              className="block text-sm font-medium text-ink"
            >
              Display name
            </label>
            <input
              id="signup-name"
              type="text"
              autoComplete="name"
              required
              minLength={2}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="Dr Jane Doe"
            />
          </div>

          <div>
            <label
              htmlFor="signup-email"
              className="block text-sm font-medium text-ink"
            >
              Email
            </label>
            <input
              id="signup-email"
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
            <label
              htmlFor="signup-password"
              className="block text-sm font-medium text-ink"
            >
              Password
            </label>
            <input
              id="signup-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={PASSWORD_MIN_LENGTH}
              pattern={PASSWORD_PATTERN}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder={`At least ${PASSWORD_MIN_LENGTH} characters`}
              aria-describedby="signup-password-hint"
            />
            <p
              id="signup-password-hint"
              className="mt-1 text-xs text-ink-soft"
            >
              {PASSWORD_HINT}
            </p>
          </div>

          <label className="flex items-start gap-2 text-xs text-ink-muted">
            <input
              type="checkbox"
              checked={acceptedTerms}
              onChange={(e) => setAcceptedTerms(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-accent focus:ring-accent"
              data-testid="signup-terms"
            />
            <span>
              I agree to the{' '}
              <Link to="/docs#terms" className="link-soft">
                terms of service
              </Link>{' '}
              and{' '}
              <Link to="/docs#privacy" className="link-soft">
                privacy policy
              </Link>
              .
            </span>
          </label>

          {error ? (
            <div
              role="alert"
              data-testid="signup-error"
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
            data-testid="signup-submit"
          >
            {submitting ? (
              <>
                <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
                Creating your account…
              </>
            ) : (
              <>
                Start free trial
                <ArrowRight aria-hidden className="h-4 w-4" />
              </>
            )}
          </button>

          <p className="text-center text-xs text-ink-muted">
            Already have an account?{' '}
            <Link to="/login" className="link-soft">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}

function SignupSuccess({ account }: { account: LicenseAccount }) {
  const expires = account.trial_expires_at
    ? new Date(account.trial_expires_at)
    : null
  return (
    <div className="py-16 sm:py-20">
      <div className="container-narrow max-w-lg">
        <div
          data-testid="signup-success"
          className="rounded-2xl border border-emerald-200 bg-emerald-50 p-8 text-center"
        >
          <CheckCircle2
            aria-hidden
            className="mx-auto h-12 w-12 text-emerald-600"
          />
          <h1 className="mt-4 text-2xl font-semibold tracking-tight text-ink">
            Your {TRIAL_DAYS}-day trial is active!
          </h1>
          <p className="mt-2 text-sm text-ink-muted">
            We&rsquo;ve sent a confirmation to{' '}
            <strong data-testid="signup-success-email">{account.email}</strong>
            .
          </p>
          {expires ? (
            <p className="mt-1 text-xs text-ink-soft">
              Trial expires on{' '}
              <strong>
                {expires.toLocaleDateString('en-GB', {
                  day: '2-digit',
                  month: 'long',
                  year: 'numeric',
                })}
              </strong>
              .
            </p>
          ) : null}
        </div>

        <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
          <h2 className="text-lg font-semibold">Next: download the app</h2>
          <p className="mt-1 text-sm text-ink-muted">
            On first launch, paste in the same email + password you just used
            to sign up. The app will activate your trial automatically.
          </p>
          <Link
            to="/install"
            className="btn-primary mt-6 w-full"
            data-testid="signup-download-cta"
          >
            <Download aria-hidden className="h-4 w-4" />
            Download the app
          </Link>
          <Link
            to="/login"
            className="mt-4 block text-center text-xs text-ink-muted hover:text-ink"
          >
            Or sign in to manage your account
          </Link>
        </div>
      </div>
    </div>
  )
}
