import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Apple, Monitor, Terminal, Download, ShieldAlert, ExternalLink, UserPlus } from 'lucide-react'
import { detectOS, downloadUrlFor, type DetectedOS, type OSDetection } from '@/lib/detectOS'
import { TRIAL_DAYS } from '@/lib/licenseApi'
import { ScreenshotFrame } from '@/components/ScreenshotFrame'

interface PlatformCard {
  key: DetectedOS
  title: string
  icon: typeof Apple
  buttonLabel: string
  warning: string
  instructions: string[]
}

const PLATFORMS: PlatformCard[] = [
  {
    key: 'mac',
    title: 'macOS',
    icon: Apple,
    buttonLabel: 'Download .dmg',
    warning:
      "When macOS says 'cannot be opened because the developer cannot be verified', right-click the app → Open → Open anyway. This is normal for unsigned apps — we're a small team and Apple charges $99/yr for signing.",
    instructions: [
      'Open the downloaded Research-Assistant-Mac.dmg.',
      'Drag Research Assistant into your Applications folder.',
      'Right-click → Open → Open anyway the first time.',
      'On Apple silicon Macs you may also need: System Settings → Privacy &amp; Security → "Open anyway".',
    ],
  },
  {
    key: 'win',
    title: 'Windows',
    icon: Monitor,
    buttonLabel: 'Download .exe',
    warning:
      "When SmartScreen blocks the installer, click 'More info' → 'Run anyway'. Same reason: an EV code-signing certificate costs ~$300/yr.",
    instructions: [
      'Run Research-Assistant-Win.exe.',
      "If SmartScreen pops up, click 'More info' then 'Run anyway'.",
      'Follow the installer prompts (it installs to %LocalAppData% by default — no admin required).',
      'Launch from the Start menu shortcut once the installer finishes.',
    ],
  },
  {
    key: 'linux',
    title: 'Linux',
    icon: Terminal,
    buttonLabel: 'Download .AppImage',
    warning:
      'AppImages are unsigned by design — verify the SHA256 from the GitHub release page if you want extra assurance.',
    instructions: [
      'Download Research-Assistant-Linux.AppImage.',
      'Make it executable: `chmod +x Research-Assistant-Linux.AppImage`.',
      'Double-click to run, or invoke it from a terminal.',
      'Optional: integrate with your menu using AppImageLauncher.',
    ],
  },
]

export default function InstallPage() {
  const [detection, setDetection] = useState<OSDetection>({ os: 'mac', isMobile: false, source: 'fallback' })

  useEffect(() => {
    setDetection(detectOS())
  }, [])

  return (
    <div className="py-16 sm:py-20">
      <div className="container-wide">
        <header className="mx-auto max-w-2xl text-center">
          <span className="badge-soft">Install</span>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">Get Research Assistant</h1>
          <p className="mt-4 text-base text-ink-muted">
            We detected you&rsquo;re on <strong>{platformLabel(detection.os)}</strong>. The matching card below is
            highlighted, but you can pick any platform.
          </p>
          {detection.isMobile ? (
            <p className="mt-3 text-sm text-amber-700">
              Heads-up: you appear to be on a mobile device. Install Research Assistant on a laptop first, then
              follow the{' '}
              <a href="/sync" className="link-soft">
                Sync guide
              </a>{' '}
              to open the PWA on your phone.
            </p>
          ) : null}
          <div
            data-testid="install-account-callout"
            className="mt-6 inline-flex items-center gap-3 rounded-2xl border border-accent/30 bg-accent-tint/40 px-4 py-3 text-left text-sm text-ink"
          >
            <UserPlus aria-hidden className="h-5 w-5 shrink-0 text-accent" />
            <span>
              You&rsquo;ll need an account to activate the app — sign up first
              for a free {TRIAL_DAYS}-day trial.{' '}
              <Link to="/signup" className="link-soft">
                Start free trial
              </Link>
              .
            </span>
          </div>
        </header>

        {/* Phase D3 — drop the dashboard screenshot below the hero copy
            so the visitor knows exactly what they'll see when they
            launch the app. */}
        <div className="mx-auto mt-12 max-w-4xl">
          <ScreenshotFrame
            src="/screenshots/dashboard.png"
            alt="Research Assistant dashboard with three demo projects"
            urlLabel="manuscripts.local"
          />
        </div>

        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          {PLATFORMS.map((p) => {
            const Icon = p.icon
            const isActive = p.key === detection.os
            return (
              <article
                key={p.key}
                data-testid={`platform-card-${p.key}`}
                data-active={isActive ? 'true' : 'false'}
                className={[
                  'surface-card flex flex-col transition-all',
                  isActive ? 'ring-2 ring-accent ring-offset-2 ring-offset-workspace' : '',
                ].join(' ')}
              >
                <header className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-sidebar text-sidebar-foreground">
                      <Icon aria-hidden className="h-5 w-5" />
                    </span>
                    <div>
                      <h2 className="text-lg font-semibold">{p.title}</h2>
                      {isActive ? <span className="text-xs text-accent">Detected on this device</span> : null}
                    </div>
                  </div>
                </header>

                <a
                  className="btn-primary mt-6"
                  href={downloadUrlFor(p.key)}
                  data-testid={`download-${p.key}`}
                >
                  <Download aria-hidden className="h-4 w-4" />
                  {p.buttonLabel}
                </a>

                <h3 className="mt-6 text-sm font-semibold uppercase tracking-wide text-ink-soft">
                  First-launch steps
                </h3>
                <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-ink-muted">
                  {p.instructions.map((step) => (
                    <li key={step}>{step}</li>
                  ))}
                </ol>

                <aside className="mt-6 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-relaxed text-amber-900">
                  <ShieldAlert aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{p.warning}</span>
                </aside>
              </article>
            )
          })}
        </div>

        <section className="mt-16 rounded-3xl border border-slate-200 bg-white px-8 py-10">
          <h2 className="text-2xl font-semibold tracking-tight">Why these warnings?</h2>
          <p className="mt-3 max-w-3xl text-sm leading-relaxed text-ink-muted">
            Operating systems flag any executable that isn&rsquo;t signed with an OS-vendor certificate. Apple
            charges $99/year for a Developer ID; Microsoft EV signing runs roughly $300/year via a third-party
            certificate authority. For a free, open source project run by a small team, we&rsquo;ve chosen to ship
            unsigned binaries and document the override flow rather than gate access behind certificate fees.
            Every release SHA256 is published on the{' '}
            <a
              className="link-soft inline-flex items-center gap-1"
              href="https://github.com/inayatpanda/research-assistant/releases"
              target="_blank"
              rel="noreferrer"
            >
              GitHub Releases page
              <ExternalLink aria-hidden className="h-3 w-3" />
            </a>{' '}
            so you can verify exactly what you downloaded.
          </p>
        </section>
      </div>
    </div>
  )
}

function platformLabel(os: DetectedOS): string {
  if (os === 'mac') return 'macOS'
  if (os === 'win') return 'Windows'
  return 'Linux'
}
