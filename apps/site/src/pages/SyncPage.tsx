import { Download, KeyRound, Smartphone, ExternalLink, Users, Network } from 'lucide-react'
import { AccordionItem, Accordion } from '@/components/Accordion'
import { ArchitectureDiagram } from '@/components/ArchitectureDiagram'

const STEPS = [
  {
    icon: Download,
    title: '1. Install Tailscale on your laptop',
    body: (
      <>
        Tailscale is a free WireGuard-based mesh VPN. Install it on the same laptop you put Research Assistant on:
        <ul className="mt-3 space-y-1 text-sm">
          <li>
            <a
              className="link-soft inline-flex items-center gap-1"
              target="_blank"
              rel="noreferrer"
              href="https://tailscale.com/download/mac"
            >
              tailscale.com/download/mac
              <ExternalLink aria-hidden className="h-3 w-3" />
            </a>
          </li>
          <li>
            <a
              className="link-soft inline-flex items-center gap-1"
              target="_blank"
              rel="noreferrer"
              href="https://tailscale.com/download/windows"
            >
              tailscale.com/download/windows
              <ExternalLink aria-hidden className="h-3 w-3" />
            </a>
          </li>
          <li>
            <a
              className="link-soft inline-flex items-center gap-1"
              target="_blank"
              rel="noreferrer"
              href="https://tailscale.com/download/linux"
            >
              tailscale.com/download/linux
              <ExternalLink aria-hidden className="h-3 w-3" />
            </a>
          </li>
        </ul>
      </>
    ),
  },
  {
    icon: KeyRound,
    title: '2. Sign in to Tailscale',
    body: (
      <>
        Use your Google, Microsoft, GitHub or Apple account. Tailscale is free for personal use up to 100
        devices and 3 users — more than enough for a typical research team. Once authenticated your laptop
        joins your <em>tailnet</em>: a private network only your devices can reach.
      </>
    ),
  },
  {
    icon: Smartphone,
    title: '3. Open Research Assistant on your phone',
    body: (
      <>
        Inside the desktop app open <strong>File → Show tailnet URL</strong> and copy the
        <code className="mx-1 rounded bg-slate-100 px-1 py-0.5 text-xs">https://your-laptop.tail-XXXX.ts.net</code>
        address. On your iPad or iPhone open Safari (or Chrome on Android), paste the URL, then choose
        <strong> Share → Add to Home Screen</strong> to install the PWA. From now on you can read, highlight
        and run a quick stats wizard from the couch — the data still lives on your laptop.
      </>
    ),
  },
] as const

export default function SyncPage() {
  return (
    <div className="py-16 sm:py-20">
      <div className="container-wide grid gap-12 lg:grid-cols-[1fr_320px]">
        <div>
          <header>
            <span className="badge-soft">Sync</span>
            <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">
              Use the app from your phone.
            </h1>
            <p className="mt-4 max-w-2xl text-base text-ink-muted">
              Three steps to get Research Assistant on your iPad or iPhone over a private Tailscale tunnel. No
              cloud account, no public URL, no firewall changes.
            </p>
          </header>

          {/* Phase D3 — embed the same architecture diagram from the home page
              at the top of the sync page so the picture-precedes-words flow
              from the marketing site carries into the docs. */}
          <div className="mt-10 rounded-2xl border border-slate-200/80 bg-white p-8 shadow-card">
            <ArchitectureDiagram />
          </div>

          <ol className="mt-12 space-y-6" data-testid="sync-steps">
            {STEPS.map(({ icon: Icon, title, body }) => (
              <li key={title} className="surface-card flex gap-5">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-tint text-accent">
                  <Icon aria-hidden className="h-5 w-5" />
                </span>
                <div>
                  <h2 className="text-lg font-semibold">{title}</h2>
                  <div className="mt-2 text-sm leading-relaxed text-ink-muted">{body}</div>
                </div>
              </li>
            ))}
          </ol>

          <section className="mt-12">
            <h2 className="text-2xl font-semibold tracking-tight">Troubleshooting</h2>
            <p className="mt-2 text-sm text-ink-muted">
              The most common issues we&rsquo;ve seen and how to fix them.
            </p>
            <div className="mt-5">
              <Accordion>
                <AccordionItem question="The app says 'Tailscale not detected'">
                  Make sure the Tailscale menu-bar icon is green. On macOS you may need to
                  &ldquo;Connect&rdquo; from the menu, and grant the Network Extension permission the first
                  time. Restart Research Assistant after Tailscale comes up.
                </AccordionItem>
                <AccordionItem question="My phone can't reach the laptop URL">
                  Both devices must be signed into the <strong>same Tailscale account</strong>. Open the
                  Tailscale app on your phone and confirm your laptop appears in the device list. If it does,
                  try MagicDNS off/on, or use the laptop&rsquo;s tailnet IP (100.x.y.z) instead of its hostname.
                </AccordionItem>
                <AccordionItem question="The app port is already in use">
                  Research Assistant binds to port 8000 (API) and 5173 (web). If another app holds those
                  ports the desktop binary will choose the next free pair and update the &ldquo;Show tailnet URL&rdquo;
                  command automatically — re-copy after the next launch.
                </AccordionItem>
                <AccordionItem question="HTTPS warnings on the PWA">
                  Tailscale issues a free Let&rsquo;s Encrypt cert via <code>tailscale cert</code>. See the
                  HTTPS-over-tailnet section in the desktop README — it takes one terminal command.
                </AccordionItem>
              </Accordion>
            </div>
          </section>
        </div>

        <aside className="space-y-6 lg:sticky lg:top-24 lg:self-start">
          <section className="surface-card">
            <div className="flex items-center gap-2 text-sm font-semibold text-accent">
              <Network aria-hidden className="h-4 w-4" />
              Why Tailscale?
            </div>
            <p className="mt-3 text-sm leading-relaxed text-ink-muted">
              Tailscale gives you an encrypted point-to-point connection between your laptop and your phone
              without exposing anything to the public internet. The data never leaves your devices, so your
              project stays as private as it would be if you only ran the app locally.
            </p>
          </section>
          <section className="surface-card">
            <div className="flex items-center gap-2 text-sm font-semibold text-accent">
              <Users aria-hidden className="h-4 w-4" />
              Inviting collaborators
            </div>
            <p className="mt-3 text-sm leading-relaxed text-ink-muted">
              From Settings → Sharing, invite a co-author by email. They&rsquo;ll receive a one-time link; once
              accepted they appear on your tailnet&rsquo;s Users tab and can open the same project URL on their
              own device. Role-based access (Owner / Editor / Commenter / Viewer) is enforced by the app.
            </p>
          </section>
        </aside>
      </div>
    </div>
  )
}
