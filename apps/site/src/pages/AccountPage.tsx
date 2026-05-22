/**
 * Phase L1c.4 — Account page.
 *
 * Requires a token in localStorage. Fetches /api/account on mount; if
 * the token is missing or invalid, redirects to /login. The device
 * list is read-only here (revoke happens in-app at Settings → License).
 */
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Loader2,
  RefreshCw,
  LogOut,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  Monitor,
} from 'lucide-react'
import {
  LEMON_SQUEEZY_CHECKOUT_URL,
  LIFETIME_PRICE_USD,
  LicenseError,
  clearSessionToken,
  humaniseError,
  licenseApi,
  loadSessionToken,
  type LicenseAccountResponse,
  type LicenseSession,
} from '@/lib/licenseApi'

export default function AccountPage() {
  const navigate = useNavigate()
  const [data, setData] = useState<LicenseAccountResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function load(initial: boolean) {
    const token = loadSessionToken()
    if (!token) {
      navigate('/login')
      return
    }
    if (initial) setLoading(true)
    else setRefreshing(true)
    setError(null)
    try {
      const res = await licenseApi.account(token)
      setData(res)
    } catch (err) {
      if (err instanceof LicenseError && err.status === 401) {
        clearSessionToken()
        navigate('/login')
        return
      }
      setError(humaniseError(err))
    } finally {
      if (initial) setLoading(false)
      else setRefreshing(false)
    }
  }

  useEffect(() => {
    void load(true)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleLogout() {
    const token = loadSessionToken()
    if (token) {
      try {
        await licenseApi.logout(token)
      } catch {
        /* best-effort */
      }
    }
    clearSessionToken()
    navigate('/login')
  }

  if (loading) {
    return (
      <div className="py-16 sm:py-20">
        <div className="container-narrow flex items-center justify-center gap-2 text-sm text-ink-muted">
          <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
          Loading your account…
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="py-16 sm:py-20">
        <div className="container-narrow max-w-md text-center">
          <p className="text-sm text-rose-700">
            {error ?? 'Something went wrong loading your account.'}
          </p>
          <button
            onClick={() => void load(true)}
            className="btn-secondary mt-4"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  const { account, devices } = data
  const isTrial = account.type === 'trial'
  const isLifetime = account.type === 'lifetime'
  const trialMs = account.trial_expires_at
    ? account.trial_expires_at - Date.now()
    : null
  const trialDays =
    trialMs !== null ? Math.max(0, Math.ceil(trialMs / (24 * 60 * 60 * 1000))) : null
  const memberSince = account.created_at
    ? new Date(account.created_at)
    : null

  return (
    <div className="py-16 sm:py-20">
      <div className="container-wide max-w-4xl">
        <header className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <span className="badge-soft">Account</span>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
              Hi, {account.display_name}
            </h1>
            <p className="mt-2 text-sm text-ink-muted">{account.email}</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => void load(false)}
              disabled={refreshing}
              className="btn-secondary disabled:opacity-60"
              data-testid="account-refresh"
            >
              <RefreshCw
                aria-hidden
                className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`}
              />
              Refresh
            </button>
            <button
              onClick={() => void handleLogout()}
              className="btn-secondary"
              data-testid="account-logout"
            >
              <LogOut aria-hidden className="h-4 w-4" />
              Log out
            </button>
          </div>
        </header>

        {/* Status card */}
        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
          <div className="flex items-start gap-4">
            <span
              className={`flex h-12 w-12 items-center justify-center rounded-xl ${
                isLifetime
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-accent-tint text-accent'
              }`}
            >
              {isLifetime ? (
                <ShieldCheck aria-hidden className="h-6 w-6" />
              ) : (
                <Sparkles aria-hidden className="h-6 w-6" />
              )}
            </span>
            <div className="flex-1">
              <h2 className="text-lg font-semibold">
                {isLifetime
                  ? 'Lifetime licence'
                  : isTrial
                    ? `Trial — ${trialDays} day${trialDays === 1 ? '' : 's'} remaining`
                    : 'Account revoked'}
              </h2>
              <p className="mt-1 text-sm text-ink-muted" data-testid="account-status">
                {isLifetime
                  ? 'You have full access to every module — and every future update.'
                  : isTrial
                    ? 'You have full access during your trial. Upgrade any time.'
                    : 'Your licence has been revoked. Contact support to restore access.'}
              </p>
              {memberSince ? (
                <p className="mt-2 text-xs text-ink-soft">
                  Member since{' '}
                  {memberSince.toLocaleDateString('en-GB', {
                    day: '2-digit',
                    month: 'long',
                    year: 'numeric',
                  })}
                </p>
              ) : null}
            </div>
          </div>

          {isTrial ? (
            <div className="mt-6 rounded-xl border border-accent/30 bg-accent-tint/30 p-4">
              <p className="text-sm font-semibold text-ink">
                Upgrade to lifetime — ${LIFETIME_PRICE_USD}
              </p>
              <p className="mt-1 text-xs text-ink-muted">
                Pay once, use forever, all future updates included. After
                purchase, come back here and click <strong>Refresh</strong> to
                pick up your new lifetime status.
              </p>
              <a
                href={LEMON_SQUEEZY_CHECKOUT_URL}
                target="_blank"
                rel="noreferrer"
                className="btn-primary mt-4"
                data-testid="account-upgrade-cta"
              >
                Buy lifetime — ${LIFETIME_PRICE_USD}
                <ArrowRight aria-hidden className="h-4 w-4" />
              </a>
            </div>
          ) : null}
        </section>

        {/* Devices */}
        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-semibold">Active devices</h2>
              <p className="mt-1 text-sm text-ink-muted">
                {devices.length} of 5 slots in use. Revoke devices from the
                app: <strong>Settings → License → Manage devices</strong>.
              </p>
            </div>
          </div>
          <ul className="mt-4 divide-y divide-slate-200">
            {devices.map((d) => (
              <DeviceRow key={d.id} device={d} />
            ))}
          </ul>
        </section>

        <p className="mt-8 text-center text-xs text-ink-soft">
          Need help?{' '}
          <Link to="/docs" className="link-soft">
            Read the docs
          </Link>{' '}
          or email{' '}
          <a href="mailto:support@research-assistant.dev" className="link-soft">
            support@research-assistant.dev
          </a>
          .
        </p>
      </div>
    </div>
  )
}

function DeviceRow({ device }: { device: LicenseSession }) {
  const lastSeen = new Date(device.last_seen_at)
  return (
    <li className="flex items-center justify-between gap-4 py-3">
      <div className="flex items-center gap-3">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100 text-ink-muted">
          <Monitor aria-hidden className="h-4 w-4" />
        </span>
        <div>
          <p className="text-sm font-medium text-ink">
            {device.device_label ?? 'Unknown device'}
          </p>
          <p className="text-xs text-ink-soft">
            Last seen {lastSeen.toLocaleString('en-GB')}
          </p>
        </div>
      </div>
    </li>
  )
}
