/**
 * Phase L1b — Dialog for managing the licensee's active devices.
 *
 * Used by:
 *   - Settings -> LicenseStatusCard ("Manage devices…")
 *   - LicensePage on a 409 device_limit_exceeded response, where the
 *     user must revoke one before they can sign in on a new device.
 */
import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { LicenseDevice } from '@/lib/licenseApi'

interface Props {
  open: boolean
  onOpenChange(open: boolean): void
  devices: LicenseDevice[]
  currentSessionId?: string | null
  /** Returns once the revocation has completed (or thrown). */
  onRevoke(sessionId: string): Promise<void>
  /** Optional explanatory copy shown above the list (e.g. "5/5 devices"). */
  description?: string
}

function formatRelative(timestamp: number): string {
  const diff = Date.now() - timestamp
  if (diff < 60_000) return 'just now'
  if (diff < 60 * 60_000) return `${Math.floor(diff / 60_000)}m ago`
  if (diff < 24 * 60 * 60_000) return `${Math.floor(diff / (60 * 60_000))}h ago`
  const days = Math.floor(diff / (24 * 60 * 60_000))
  return `${days}d ago`
}

export function DeviceManagementDialog({
  open,
  onOpenChange,
  devices,
  currentSessionId,
  onRevoke,
  description,
}: Props) {
  const [busyId, setBusyId] = useState<string | null>(null)
  const [errorId, setErrorId] = useState<string | null>(null)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="device-manager-dialog">
        <DialogHeader>
          <DialogTitle>Active devices</DialogTitle>
          <DialogDescription>
            {description ??
              'These devices are currently signed in to your account.'}
          </DialogDescription>
        </DialogHeader>
        <ul className="divide-y divide-border">
          {devices.length === 0 && (
            <li className="py-3 text-[13px] text-muted-foreground">
              No active devices.
            </li>
          )}
          {devices.map((d) => {
            const isCurrent = d.id === currentSessionId
            return (
              <li
                key={d.id}
                data-testid={`device-row-${d.id}`}
                className="flex items-center justify-between py-3"
              >
                <div className="min-w-0 flex-1 pr-4">
                  <div className="flex items-center gap-2 text-[14px] font-medium">
                    {d.device_label ?? 'Unknown device'}
                    {isCurrent && (
                      <Badge variant="secondary" className="text-[10px]">
                        this device
                      </Badge>
                    )}
                  </div>
                  <div className="mt-0.5 text-[11px] text-muted-foreground truncate">
                    Last seen {formatRelative(d.last_seen_at)}
                    {d.ip ? ` · ${d.ip}` : ''}
                  </div>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={isCurrent || busyId === d.id}
                  onClick={async () => {
                    setBusyId(d.id)
                    setErrorId(null)
                    try {
                      await onRevoke(d.id)
                    } catch {
                      setErrorId(d.id)
                    } finally {
                      setBusyId(null)
                    }
                  }}
                >
                  {busyId === d.id ? 'Revoking…' : 'Revoke'}
                </Button>
              </li>
            )
          })}
        </ul>
        {errorId && (
          <div className="text-[12px] text-rose-600">
            Failed to revoke that device. Please try again.
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
