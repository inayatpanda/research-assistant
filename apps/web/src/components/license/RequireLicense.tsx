/**
 * Phase L1b — Licence gate that wraps the existing per-install
 * ``<RequireAuth>`` subtree. Layering: RequireLicense -> RequireAuth -> Routes.
 *
 * Decision tree on mount:
 *   - No token in store               => redirect to /license
 *   - Stale (older than 7d) + verify ok => bump lastVerifiedAt, allow
 *   - Stale + 401                     => clear + redirect to /license
 *   - Stale + network failure + still within 7d => offline grace, allow
 *   - Account type === 'revoked'      => /license with banner
 *   - Trial expired                   => /upgrade
 */
import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { LicenseError, licenseApi } from '@/lib/licenseApi'
import {
  isAccountUsable,
  isLicenseFresh,
  useLicenseStore,
} from '@/lib/licenseStore'

type Status = 'checking' | 'ok' | 'revoked' | 'trial_expired' | 'unauthed'

export function RequireLicense({ children }: { children: ReactNode }) {
  const location = useLocation()
  const token = useLicenseStore((s) => s.token)
  const account = useLicenseStore((s) => s.account)
  const setLastVerified = useLicenseStore((s) => s.setLastVerified)
  const setAccount = useLicenseStore((s) => s.setAccount)
  const clear = useLicenseStore((s) => s.clear)

  const initialFresh = isLicenseFresh()
  const initialUsable = isAccountUsable(account)

  const [status, setStatus] = useState<Status>(() => {
    if (!token || !account) return 'unauthed'
    if (account.type === 'revoked') return 'revoked'
    if (!initialUsable && account.type === 'trial') return 'trial_expired'
    // If fresh + usable we can skip the verify roundtrip on this render.
    if (initialFresh) return 'ok'
    return 'checking'
  })

  useEffect(() => {
    if (status !== 'checking') return
    let cancelled = false
    ;(async () => {
      try {
        if (!token) {
          if (!cancelled) setStatus('unauthed')
          return
        }
        const res = await licenseApi.verify(token)
        if (cancelled) return
        setAccount(res.account)
        setLastVerified(Date.now())
        if (res.account.type === 'revoked') {
          setStatus('revoked')
          return
        }
        if (!isAccountUsable(res.account)) {
          setStatus('trial_expired')
          return
        }
        setStatus('ok')
      } catch (err) {
        if (cancelled) return
        if (err instanceof LicenseError) {
          if (err.status === 401 || err.code === 'account_revoked') {
            clear()
            setStatus(err.code === 'account_revoked' ? 'revoked' : 'unauthed')
            return
          }
          if (err.code === 'network_error') {
            // Offline grace: if our last successful verify is still within
            // the 7-day window, allow the app to launch.
            if (isLicenseFresh()) {
              setStatus('ok')
              return
            }
            setStatus('unauthed')
            return
          }
        }
        // Unknown error — be conservative and bounce to /license.
        setStatus('unauthed')
      }
    })()
    return () => {
      cancelled = true
    }
  }, [status, token, setAccount, setLastVerified, clear])

  if (status === 'checking') {
    return (
      <div
        data-testid="license-gate-loading"
        className="flex h-full w-full items-center justify-center text-sm text-muted-foreground"
      >
        Checking your licence…
      </div>
    )
  }
  if (status === 'unauthed') {
    return (
      <Navigate
        to="/license"
        replace
        state={{ from: location.pathname + location.search }}
      />
    )
  }
  if (status === 'revoked') {
    return (
      <Navigate
        to="/license"
        replace
        state={{
          from: location.pathname + location.search,
          banner:
            'Your licence has been revoked. Contact support if you think this is a mistake.',
        }}
      />
    )
  }
  if (status === 'trial_expired') {
    return <Navigate to="/upgrade" replace />
  }
  return <>{children}</>
}

export default RequireLicense
