/**
 * Phase M0.6 — Settings card: "Force desktop layout".
 *
 * Lets power users on small screens (notably iPad) opt out of the
 * mobile shell that <DeviceRouter> renders below 900px. Wired to the
 * persisted ``useForceDesktop`` store so the choice survives reloads
 * and home-screen relaunches.
 */
import { Smartphone } from 'lucide-react'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { useForceDesktop } from '@/mobile/lib/forceDesktop'

export function ForceDesktopCard() {
  const enabled = useForceDesktop((s) => s.enabled)
  const setEnabled = useForceDesktop((s) => s.set)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-[15px]">Layout</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-start gap-3">
          <Smartphone className="h-4 w-4 mt-[2px] text-muted-foreground shrink-0" />
          <div className="min-w-0 flex-1">
            <Label
              htmlFor="force-desktop-toggle"
              className="text-[13px] font-medium cursor-pointer"
            >
              Force desktop layout
            </Label>
            <div className="text-[12px] text-muted-foreground mt-0.5">
              Always show the desktop view, even on small screens. Useful for
              previewing or for power users on iPad.
            </div>
          </div>
          {/* Native checkbox styled as a switch — keeps the dependency
              graph tiny (no @radix-ui/react-switch). */}
          <input
            id="force-desktop-toggle"
            type="checkbox"
            role="switch"
            aria-label="Force desktop layout"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="h-4 w-4 cursor-pointer accent-primary"
          />
        </div>
      </CardContent>
    </Card>
  )
}
