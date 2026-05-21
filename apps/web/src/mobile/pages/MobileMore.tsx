/**
 * Phase M1.4 — Mobile "More" tab.
 *
 * Long single-column list of less-frequent actions:
 *   - Account    (current email, manage, logout)
 *   - Tools      (Peer Review live, others labelled "Coming soon")
 *   - Settings   (settings, force-desktop toggle)
 *   - About      (version sheet, tailscale help link)
 */
import { useMutation } from '@tanstack/react-query'
import {
  BarChart3,
  CheckSquare,
  FileQuestion,
  Info,
  LogOut,
  Network,
  Settings as SettingsIcon,
  Stethoscope,
  User as UserIcon,
} from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useCurrentUser } from '@/hooks/useAuth'
import { authApi } from '@/lib/api'

import { BottomSheet } from '../components/BottomSheet'
import { MobileList, MobileListRow } from '../components/MobileList'
import { useForceDesktop } from '../lib/forceDesktop'

const APP_VERSION = '1.0.0-m1'
const BUILD_DATE = '2026-05-21'

export default function MobileMore() {
  const navigate = useNavigate()
  const { data: user } = useCurrentUser()
  const force = useForceDesktop((s) => s.enabled)
  const setForce = useForceDesktop((s) => s.set)
  const [aboutOpen, setAboutOpen] = useState(false)

  const logout = useMutation({
    mutationFn: () => authApi.logout(),
    onSettled: () => {
      navigate('/login', { replace: true })
    },
  })

  return (
    <div className="flex min-h-full flex-col bg-background pb-6">
      <div className="px-4 pt-4 pb-3">
        <h2 className="text-[20px] font-semibold tracking-tight">More</h2>
      </div>

      <div className="space-y-4">
        <MobileList groupTitle="Account">
          <MobileListRow
            icon={UserIcon}
            title={user?.display_name || user?.email || 'Signed in'}
            subtitle={user?.email}
            static
            data-testid="mmore-account-email"
          />
          <MobileListRow
            title="Manage account"
            onClick={() => navigate('/m/account')}
            data-testid="mmore-manage-account"
          />
          <MobileListRow
            icon={LogOut}
            title="Log out"
            onClick={() => logout.mutate()}
            data-testid="mmore-logout"
          />
        </MobileList>

        <MobileList groupTitle="Tools">
          <MobileListRow
            icon={Stethoscope}
            title="Peer review"
            subtitle="AI critique for manuscripts and uploaded PDFs"
            onClick={() => navigate('/m/peer-review')}
            data-testid="mmore-peer-review"
          />
          <MobileListRow
            icon={BarChart3}
            title="Economics"
            subtitle="ICER / QALY / NMB quick calculators"
            onClick={() => navigate('/m/economics')}
            data-testid="mmore-economics"
          />
          <MobileListRow
            icon={CheckSquare}
            title="Checklists"
            subtitle="CONSORT, PRISMA, STROBE and 9 more"
            onClick={() => navigate('/m/checklists')}
            data-testid="mmore-checklists"
          />
          <MobileListRow
            icon={FileQuestion}
            title="Submission"
            subtitle="Cover letter, reviewer replies, package"
            onClick={() => navigate('/m/submission')}
            data-testid="mmore-submission"
          />
        </MobileList>

        <MobileList groupTitle="Settings">
          <MobileListRow
            icon={SettingsIcon}
            title="Settings"
            subtitle="AI providers, storage, journal templates"
            onClick={() => navigate('/m/settings')}
            data-testid="mmore-settings"
          />
          <MobileListRow
            title="Force desktop layout"
            subtitle="Always render the desktop UI on this device"
            static
            trailing={
              <input
                type="checkbox"
                role="switch"
                aria-label="Force desktop layout"
                data-testid="mmore-force-desktop"
                checked={force}
                onChange={(e) => setForce(e.target.checked)}
                className="h-4 w-4 cursor-pointer accent-primary"
              />
            }
          />
        </MobileList>

        <MobileList groupTitle="About">
          <MobileListRow
            icon={Info}
            title="About this app"
            subtitle="Version and build info"
            onClick={() => setAboutOpen(true)}
            data-testid="mmore-about"
          />
          <MobileListRow
            icon={Network}
            title="Tailscale setup help"
            subtitle="How the mobile app talks to your laptop"
            onClick={() => navigate('/m/setup-help')}
            data-testid="mmore-tailscale-help"
          />
        </MobileList>
      </div>

      <BottomSheet
        open={aboutOpen}
        onClose={() => setAboutOpen(false)}
        title="About"
        snapPoints={['50%']}
      >
        <div className="space-y-3 py-2 text-[14px]">
          <div className="flex justify-between border-b border-border pb-2">
            <span className="text-muted-foreground">App</span>
            <span className="font-medium">Research Assistant</span>
          </div>
          <div className="flex justify-between border-b border-border pb-2">
            <span className="text-muted-foreground">Version</span>
            <span className="font-medium">{APP_VERSION}</span>
          </div>
          <div className="flex justify-between border-b border-border pb-2">
            <span className="text-muted-foreground">Built</span>
            <span className="font-medium">{BUILD_DATE}</span>
          </div>
          <p className="text-[12px] text-muted-foreground leading-relaxed pt-2">
            Mobile PWA that talks to your laptop over a Tailscale tailnet. Data
            never leaves your hardware. See "Tailscale setup help" if you need
            to install the network bridge.
          </p>
        </div>
      </BottomSheet>
    </div>
  )
}
