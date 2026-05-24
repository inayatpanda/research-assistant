import { Laptop, Network, Users } from 'lucide-react'

/**
 * Three-step explainer. Lives between the hero/trust strip and the
 * deep feature sections — answers the "what does the app actually do?"
 * question before any single feature gets a paragraph of explanation.
 *
 * Each step is a card with an icon, a short title and a sentence of
 * copy. The numbering uses a small monospaced "01"/"02"/"03" rather
 * than a circular badge because it reads as more technical, which is
 * the tone the rest of the site sets.
 */
const STEPS = [
  {
    icon: Laptop,
    title: 'Write locally',
    body: 'Your manuscript lives on your Mac, in SQLite. No cloud, no telemetry, no upload-before-you-can-edit.',
  },
  {
    icon: Network,
    title: 'Sync via Tailscale',
    body: "Open your laptop's tailnet URL on any other device — iPad on a ward round, iPhone on the bus — and keep writing.",
  },
  {
    icon: Users,
    title: 'Share with co-authors',
    body: 'Invite by email; they join your tailnet and see only the projects you share. You stay in control of every file.',
  },
] as const

export function HowItWorks() {
  return (
    <section
      id="how-it-works"
      className="border-b border-slate-200 bg-slate-50/50 py-20 sm:py-24"
      aria-labelledby="how-it-works-heading"
    >
      <div className="container-wide">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
            How it works
          </p>
          <h2
            id="how-it-works-heading"
            className="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-4xl"
          >
            One Mac. Many devices. No cloud.
          </h2>
          <p className="mt-3 text-base text-ink-muted">
            The app is a desktop tool that quietly serves itself to your other
            devices over your private Tailscale network. You stay logged in to
            one machine; everything else just reads from it.
          </p>
        </div>

        <ol
          className="mt-12 grid gap-6 md:grid-cols-3"
          data-testid="how-it-works-steps"
        >
          {STEPS.map(({ icon: Icon, title, body }, idx) => (
            <li
              key={title}
              className="group relative flex flex-col rounded-2xl border border-slate-200/80 bg-white p-6 shadow-card transition-transform hover:-translate-y-0.5"
              data-testid="how-it-works-step"
            >
              <div className="flex items-center justify-between">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-tint text-accent">
                  <Icon aria-hidden className="h-5 w-5" />
                </div>
                <span className="font-mono text-xs text-ink-soft">
                  {String(idx + 1).padStart(2, '0')}
                </span>
              </div>
              <h3 className="mt-5 text-lg font-semibold text-ink">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">{body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
