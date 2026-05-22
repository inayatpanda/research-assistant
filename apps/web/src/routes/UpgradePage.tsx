/**
 * Phase L1b — Trial-expired upgrade page.
 *
 * Public route. Shown when ``RequireLicense`` detects that the cached
 * account's ``trial_expires_at`` is in the past. The page links out to
 * Lemon Squeezy for the lifetime purchase. After paying, the user can
 * tap "Refresh" to re-verify and continue into the app.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { LicenseError, licenseApi } from '@/lib/licenseApi'
import { isAccountUsable, useLicenseStore } from '@/lib/licenseStore'

const LEMON_SQUEEZY_CHECKOUT_URL =
  'https://research-assistant.lemonsqueezy.com/buy/REPLACE-AFTER-LS-PRODUCT-CREATED'

export default function UpgradePage() {
  const navigate = useNavigate()
  const token = useLicenseStore((s) => s.token)
  const account = useLicenseStore((s) => s.account)
  const setAccount = useLicenseStore((s) => s.setAccount)
  const setLastVerified = useLicenseStore((s) => s.setLastVerified)
  const clear = useLicenseStore((s) => s.clear)

  const [refreshing, setRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState<string | null>(null)

  async function refresh() {
    if (!token) {
      navigate('/license')
      return
    }
    setRefreshing(true)
    setRefreshError(null)
    try {
      const res = await licenseApi.verify(token)
      setAccount(res.account)
      setLastVerified(Date.now())
      if (isAccountUsable(res.account)) {
        navigate('/', { replace: true })
      } else {
        setRefreshError(
          'Your trial is still expired. After purchasing, give the system a minute to register the payment, then try again.',
        )
      }
    } catch (err) {
      if (err instanceof LicenseError && err.status === 401) {
        clear()
        navigate('/license')
        return
      }
      setRefreshError(
        err instanceof LicenseError
          ? err.message
          : 'Could not reach the licence server.',
      )
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 px-4 py-10">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle className="text-[20px]">Your 30-day trial has ended</CardTitle>
          <CardDescription>
            {account?.display_name
              ? `Thanks for trying it, ${account.display_name}. To keep using Research Assistant, upgrade to the lifetime version.`
              : 'To keep using Research Assistant, upgrade to the lifetime version.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="rounded-lg border border-border bg-white px-5 py-4">
            <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              Lifetime licence
            </div>
            <div className="mt-1 flex items-baseline gap-2">
              <span className="text-3xl font-semibold tracking-tight">$29</span>
              <span className="text-[13px] text-muted-foreground">
                · pay once, use forever
              </span>
            </div>
            <ul className="mt-3 space-y-1.5 text-[13px] text-muted-foreground">
              <li>· All features, no usage limits</li>
              <li>· Works on up to 5 of your devices</li>
              <li>· All future updates included</li>
              <li>· Your data stays on your hardware</li>
            </ul>
            <a
              href={LEMON_SQUEEZY_CHECKOUT_URL}
              target="_blank"
              rel="noreferrer"
              data-testid="upgrade-checkout-link"
              className="mt-4 inline-flex w-full items-center justify-center rounded-md bg-accent px-4 py-2 text-[14px] font-medium text-white hover:bg-accent-hover"
            >
              Upgrade now — $29 lifetime
            </a>
            <p className="mt-2 text-[11px] text-muted-foreground">
              Payment handled by Lemon Squeezy. PayPal + cards accepted.
            </p>
          </div>

          <div className="space-y-2">
            <Button
              variant="outline"
              onClick={refresh}
              disabled={refreshing}
              data-testid="upgrade-refresh"
              className="w-full"
            >
              {refreshing ? 'Checking…' : 'Already purchased? Refresh licence'}
            </Button>
            {refreshError && (
              <div className="text-[12px] text-rose-700">{refreshError}</div>
            )}
          </div>

          <button
            type="button"
            className="text-[12px] text-muted-foreground hover:text-foreground hover:underline"
            onClick={() => {
              clear()
              navigate('/license')
            }}
          >
            Use a different account
          </button>
        </CardContent>
      </Card>
    </div>
  )
}
