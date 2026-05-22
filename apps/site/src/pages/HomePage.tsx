import { Link } from 'react-router-dom'
import {
  BookOpen,
  FileText,
  PenSquare,
  BarChart3,
  Network,
  ShieldCheck,
  Send,
  Smartphone,
  ArrowRight,
  Sparkles,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { detectOS, type OSDetection } from '@/lib/detectOS'
import {
  LEMON_SQUEEZY_CHECKOUT_URL,
  LIFETIME_PRICE_USD,
  TRIAL_DAYS,
} from '@/lib/licenseApi'

const FEATURES = [
  {
    icon: BookOpen,
    title: 'Library',
    body: 'Import from DOI, PubMed, RIS or BibTeX. Automatic dedup, merging and grey-literature handling.',
  },
  {
    icon: FileText,
    title: 'Reader',
    body: 'Read PDFs with colour-coded highlights, inline AI paraphrasing and per-paragraph notes.',
  },
  {
    icon: PenSquare,
    title: 'Manuscript editor',
    body: 'TipTap editor with @-citations, native tables, figures, and ordered bibliography output.',
  },
  {
    icon: BarChart3,
    title: 'Statistics',
    body: 'From t-test to mixed-effects, GEE and survival, with diagnostics, plots, and dataset transforms.',
  },
  {
    icon: Network,
    title: 'Meta-analysis',
    body: 'Forest, funnel, leave-one-out, subgroups, GRADE Summary-of-Findings, PROSPERO and living reviews.',
  },
  {
    icon: ShieldCheck,
    title: 'Peer Review',
    body: 'AI critique of your manuscript or any uploaded PDF — fairness, methods, statistics, reporting.',
  },
  {
    icon: Send,
    title: 'Submission',
    body: 'Cover letters, reviewer responses and journal-specific templates packaged into a submission zip.',
  },
  {
    icon: Smartphone,
    title: 'Mobile PWA',
    body: 'Read, highlight and run a quick stats wizard on iPad or iPhone over your private Tailscale.',
  },
] as const

const HERO_TITLE = 'Write better medical research, faster.'
const HERO_SUB =
  'A local-first manuscript assistant for clinical research — Library, Reader, Statistics, Meta-analysis, Manuscript Editor, Peer Review, all in one app.'

export default function HomePage() {
  // Client-only detection — fall back to mac on the server pre-hydration.
  // We still detect the OS so the install page link feels personal; the
  // hero CTA itself now drives signup, not direct download.
  const [, setDetection] = useState<OSDetection>({ os: 'mac', isMobile: false, source: 'fallback' })

  useEffect(() => {
    setDetection(detectOS())
  }, [])

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-slate-200 bg-gradient-to-b from-white via-white to-slate-50">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[520px] bg-[radial-gradient(60%_60%_at_50%_0%,rgba(37,99,235,0.12)_0%,rgba(255,255,255,0)_70%)]"
        />
        <div className="container-narrow flex flex-col items-center pt-16 pb-20 text-center sm:pt-24 sm:pb-28">
          <span className="badge-soft">
            <Sparkles aria-hidden className="h-3.5 w-3.5" />
            {TRIAL_DAYS}-day free trial — no card required
          </span>
          <h1 className="mt-6 max-w-3xl text-4xl font-semibold tracking-tight text-ink sm:text-5xl md:text-6xl">
            {HERO_TITLE}
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-relaxed text-ink-muted sm:text-lg">{HERO_SUB}</p>
          <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row">
            <Link className="btn-primary" to="/signup" data-testid="hero-primary-cta">
              Start free trial
              <ArrowRight aria-hidden className="h-4 w-4" />
            </Link>
            <a
              className="btn-secondary"
              href={LEMON_SQUEEZY_CHECKOUT_URL}
              target="_blank"
              rel="noreferrer"
              data-testid="hero-secondary-cta"
            >
              Buy lifetime — ${LIFETIME_PRICE_USD}
            </a>
          </div>
          <p className="mt-4 text-xs text-ink-soft">
            Already have an account?{' '}
            <Link to="/login" className="link-soft">
              Sign in
            </Link>
            .
          </p>
        </div>
      </section>

      {/* Features grid */}
      <section className="py-20 sm:py-24">
        <div className="container-wide">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
              One app, every step of the manuscript.
            </h2>
            <p className="mt-3 text-base text-ink-muted">
              Built by a clinical researcher who got tired of stitching together six different tools.
            </p>
          </div>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map(({ icon: Icon, title, body }) => (
              <article key={title} className="surface-card transition-transform hover:-translate-y-1">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-tint text-accent">
                  <Icon aria-hidden className="h-5 w-5" />
                </div>
                <h3 className="mt-4 text-base font-semibold text-ink">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-muted">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* Trust strip */}
      <section className="border-y border-slate-200 bg-white py-14">
        <div className="container-narrow text-center">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Your data lives on your laptop.
          </h2>
          <p className="mx-auto mt-3 max-w-2xl text-base text-ink-muted">
            No cloud sync. No telemetry. No hidden subscriptions. The app runs locally, talks to your own machine,
            and only reaches out when <em>you</em> ask it to fetch a DOI or PubMed record.
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3 text-xs text-ink-soft">
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1">Local SQLite</span>
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1">Tailscale-only sync</span>
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1">Open source codebase</span>
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1">No analytics</span>
          </div>
        </div>
      </section>

      {/* Footer CTA */}
      <section className="py-20 sm:py-24">
        <div className="container-narrow rounded-3xl bg-sidebar px-10 py-14 text-center text-sidebar-foreground shadow-card">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Try free for {TRIAL_DAYS} days.
          </h2>
          <p className="mt-3 text-base text-white/70">
            ${LIFETIME_PRICE_USD} once after that. No subscription, no surprises.
          </p>
          <div className="mt-7 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link to="/signup" className="btn-primary !bg-white !text-ink !shadow-none">
              Start free trial
            </Link>
            <Link
              to="/pricing"
              className="btn-secondary !border-white/20 !bg-white/10 !text-white hover:!bg-white/20"
            >
              See pricing
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
