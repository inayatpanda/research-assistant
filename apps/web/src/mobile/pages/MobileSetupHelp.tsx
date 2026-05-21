/**
 * Phase M1.4 — Tailscale setup help.
 *
 * Short read-only page explaining how to install Tailscale on Mac /
 * Windows / iPhone, where to find the laptop's tailnet URL, and what
 * the mobile app does when the laptop is offline. Linked from More →
 * "Tailscale setup help".
 */
import { useNavigate } from 'react-router-dom'

import { Card, CardContent } from '@/components/ui/card'

import { MobileHeader } from '../components/MobileHeader'

export default function MobileSetupHelp() {
  const navigate = useNavigate()
  return (
    <div className="flex min-h-full flex-col bg-background">
      <MobileHeader title="Tailscale setup" onBack={() => navigate(-1)} />

      <div className="space-y-3 px-4 py-4 text-[14px] leading-relaxed">
        <Card>
          <CardContent className="space-y-3 py-4">
            <p>
              Research Assistant doesn't ship a cloud sync server. Your mobile
              device talks directly to the laptop that hosts the backend over a
              <strong> Tailscale tailnet</strong> — a private VPN you control.
            </p>
            <p className="text-muted-foreground text-[13px]">
              Tailscale is free for personal use (up to 100 devices, 3 users).
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="py-4">
            <div className="text-[12px] uppercase tracking-wider text-muted-foreground font-medium mb-2">
              On your laptop
            </div>
            <ol className="ml-4 list-decimal space-y-2 text-[13px]">
              <li>
                Install Tailscale from{' '}
                <a
                  className="underline"
                  href="https://tailscale.com/download"
                  target="_blank"
                  rel="noreferrer"
                >
                  tailscale.com/download
                </a>{' '}
                and sign in.
              </li>
              <li>
                Open the Research Assistant desktop app and choose{' '}
                <em>Show tailnet URL</em> from the menu.
              </li>
              <li>Note the URL — it looks like <code>http://your-mac.tail-xxx.ts.net:8787</code>.</li>
            </ol>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="py-4">
            <div className="text-[12px] uppercase tracking-wider text-muted-foreground font-medium mb-2">
              On your phone or tablet
            </div>
            <ol className="ml-4 list-decimal space-y-2 text-[13px]">
              <li>Install Tailscale from the App Store / Play Store and sign in.</li>
              <li>
                Open this app. On first launch, paste the tailnet URL into the
                setup screen.
              </li>
              <li>You can change the URL later from <em>More → Settings</em>.</li>
            </ol>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-2 py-4 text-[13px]">
            <div className="text-[12px] uppercase tracking-wider text-muted-foreground font-medium mb-1">
              Offline behaviour
            </div>
            <p>
              When the laptop is asleep or off-network, reads fall back to the
              Learn cache in your device's IndexedDB. Writes (uploading PDFs,
              generating reviews) fail until the laptop is reachable again.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
