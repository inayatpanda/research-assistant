/**
 * Phase L1b — Settings card showing the current licence status.
 *
 * Displays licensee + type badge + days-remaining (if trial) + device
 * count. Buttons: Upgrade (if trial), Log out of this device, Log out
 * everywhere, Replace licence. Opens DeviceManagementDialog for revoke.
 */
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { DeviceManagementDialog } from '@/components/license/DeviceManagementDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LicenseError, licenseApi } from '@/lib/licenseApi'
import { LEMON_SQUEEZY_CHECKOUT_URL } from '@/lib/licenseConstants'
import {
  trialDaysRemaining,
  useLicenseStore,
} from '@/lib/licenseStore'

export function LicenseStatusCard() {
  const navigate = useNavigate()
  const token = useLicenseStore((s) => s.token)
  const account = useLicenseStore((s) => s.account)
  const session = useLicenseStore((s) => s.session)
  const devices = useLicenseStore((s) => s.devices)
  const setDevices = useLicenseStore((s) => s.setDevices)
  const clear = useLicenseStore((s) => s.clear)
  const setSession = useLicenseStore((s) => s.setSession)

  const [managerOpen, setManagerOpen] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)
  // Fix-E2E/5 — when the licence server is unreachable (DNS failure, offline,
  // dev without the worker running) surface a friendly hint instead of just
  // logging ERR_NAME_NOT_RESOLVED to the console.
  const [offline, setOffline] = useState(false)

  // Lazy-load fresh device list when card mounts.
  useEffect(() => {
    if (!token) return
    licenseApi
      .account(token)
      .then((res) => {
        setOffline(false)
        setDevices(res.devices)
        // Also refresh the cached account in case server-side state moved.
        setSession(token, res.account, res.session, res.devices)
      })
      .catch((err) => {
        // Network-level failures (DNS/TCP/CORS) surface as LicenseError
        // with code='network_error' and status=0. Treat as offline so the
        // user knows we're showing cached info.
        const isNetwork =
          err instanceof LicenseError &&
          (err.code === 'network_error' || err.status === 0)
        if (isNetwork) {
          setOffline(true)
        }
        /* otherwise fall back to whatever we cached, silently */
      })
  }, [token, setDevices, setSession])

  if (!account) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-[15px]">License</CardTitle>
        </CardHeader>
        <CardContent className="text-[13px] text-muted-foreground">
          Not signed in to a licence.{' '}
          <Link to="/license" className="underline">
            Sign in
          </Link>
          .
        </CardContent>
      </Card>
    )
  }

  const daysLeft = trialDaysRemaining(account)
  const deviceCount = devices?.length ?? '—'

  async function logoutThis() {
    if (!token) return
    setBusy('logout')
    try {
      await licenseApi.logout(token)
    } catch {
      /* swallow — we're tearing down anyway */
    }
    clear()
    navigate('/license')
  }

  async function logoutEverywhere() {
    if (!token) return
    setBusy('logout-all')
    try {
      await licenseApi.logoutAll(token)
    } catch {
      /* swallow */
    }
    clear()
    navigate('/license')
  }

  async function handleRevoke(sessionId: string) {
    if (!token) throw new Error('not signed in')
    try {
      await licenseApi.revokeDevice(token, sessionId)
      // Re-fetch devices.
      const res = await licenseApi.account(token)
      setDevices(res.devices)
    } catch (err) {
      if (err instanceof LicenseError && err.status === 401) {
        clear()
        navigate('/license')
      }
      throw err
    }
  }

  return (
    <Card data-testid="license-status-card">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-[15px]">License</CardTitle>
        {account.type === 'trial' && (
          <Badge
            variant="secondary"
            className="bg-amber-500/15 text-amber-700 border-amber-500/20"
          >
            Trial · {daysLeft ?? 0}d left
          </Badge>
        )}
        {account.type === 'lifetime' && (
          <Badge
            variant="default"
            className="bg-emerald-500/15 text-emerald-700 border-emerald-500/20 hover:bg-emerald-500/15"
          >
            Lifetime
          </Badge>
        )}
        {account.type === 'revoked' && (
          <Badge variant="destructive">Revoked</Badge>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <div className="text-[14px] font-medium">{account.display_name}</div>
          <div className="text-[12px] text-muted-foreground">{account.email}</div>
        </div>
        {offline && (
          <div
            data-testid="license-offline-hint"
            className="rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-[12px] text-amber-900"
          >
            Could not reach the license server. Showing cached info — Log out
            and Manage devices may not work until the connection comes back.
          </div>
        )}
        <div className="text-[12px] text-muted-foreground">
          {deviceCount} of 5 devices active ·{' '}
          <button
            type="button"
            data-testid="license-manage-devices"
            className="underline hover:text-foreground"
            onClick={() => setManagerOpen(true)}
          >
            Manage devices
          </button>
        </div>
        {account.type === 'trial' && (
          <a
            href={LEMON_SQUEEZY_CHECKOUT_URL}
            target="_blank"
            rel="noreferrer"
            data-testid="license-upgrade"
            className="inline-flex items-center justify-center rounded-md bg-accent px-3 py-1.5 text-[13px] font-medium text-white hover:bg-accent-hover"
          >
            Upgrade to lifetime — $29
          </a>
        )}
        <div className="flex flex-wrap gap-2 pt-1">
          <Button
            variant="outline"
            size="sm"
            disabled={busy !== null}
            onClick={logoutThis}
            data-testid="license-logout-this"
          >
            {busy === 'logout' ? 'Signing out…' : 'Log out'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={busy !== null}
            onClick={logoutEverywhere}
            data-testid="license-logout-all"
          >
            {busy === 'logout-all' ? 'Signing out everywhere…' : 'Log out everywhere'}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={busy !== null}
            onClick={() => {
              clear()
              navigate('/license')
            }}
          >
            Replace licence
          </Button>
        </div>
      </CardContent>
      <DeviceManagementDialog
        open={managerOpen}
        onOpenChange={setManagerOpen}
        devices={devices ?? []}
        currentSessionId={session?.id ?? null}
        description={`You can be signed in on up to 5 devices. Currently ${
          devices?.length ?? 0
        }/5.`}
        onRevoke={handleRevoke}
      />
    </Card>
  )
}

export default LicenseStatusCard
