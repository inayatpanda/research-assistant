/**
 * Phase M1.4 — Mobile account page.
 *
 * Re-uses the existing <AccountPanel> S1 component (it renders OK on
 * narrow viewports) and just gives it a mobile-friendly header + safe
 * spacing inside the MobileShell.
 */
import { AccountPanel } from '@/components/auth/AccountPanel'

import { MobileHeader } from '../components/MobileHeader'

export default function MobileAccount() {
  return (
    <div className="flex min-h-full flex-col bg-background">
      <MobileHeader title="Account" />
      <div className="px-4 py-4">
        <AccountPanel />
      </div>
    </div>
  )
}
