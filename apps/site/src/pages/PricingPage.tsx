/**
 * Phase L1c.1 — Pricing page.
 *
 * Two-card layout: free 30-day trial vs $29 lifetime. The lifetime card
 * points to the Lemon Squeezy checkout (placeholder URL until the user
 * provisions the LS product). Includes a "Why $29?" comparison and a
 * pre-purchase FAQ to address the common objections (refunds, devices,
 * laptop-died scenarios).
 */
import { Link } from 'react-router-dom'
import {
  Check,
  Sparkles,
  CreditCard,
  ShieldCheck,
  Laptop,
  RefreshCw,
  HelpCircle,
  ArrowRight,
} from 'lucide-react'
import {
  LEMON_SQUEEZY_CHECKOUT_URL,
  LIFETIME_PRICE_USD,
  TRIAL_DAYS,
  DEVICE_LIMIT,
} from '@/lib/licenseApi'

const INCLUDED_FEATURES = [
  'Library: PubMed / DOI / RIS / BibTeX import + dedup',
  'Reader: highlights, inline AI paraphrase, per-paragraph notes',
  'Manuscript editor: @-citations, tables, figures, journal templates',
  'Statistics: t-tests, regression, mixed-effects, survival, GEE',
  'Meta-analysis: forest, funnel, leave-one-out, GRADE SoF, PROSPERO',
  'Peer Review: AI critique of methods, statistics and reporting',
  'Submission: cover letters, reviewer responses, journal-specific bundles',
  'Mobile PWA: read, highlight and run stats on iPad or iPhone',
  'Local SQLite — your data stays on your laptop',
  'All future updates and modules at no extra cost',
]

const COMPARISON = [
  {
    product: 'Endnote 21',
    price: '$309 perpetual + paid upgrades',
    note: 'Citation manager only — no editor, stats, or peer review.',
  },
  {
    product: 'Zotero Pro / 6 GB storage',
    price: '~$80 per year',
    note: 'Citation manager + sync. Charges scale with library size.',
  },
  {
    product: 'Mendeley Reference Manager',
    price: 'Free, but Elsevier-owned',
    note: 'Reader + references only. Cloud-only; data lives on Elsevier servers.',
  },
  {
    product: 'GraphPad Prism (stats)',
    price: '~$300 per year (academic)',
    note: 'Stats + plots only — no manuscript editor or citations.',
  },
]

const FAQ = [
  {
    icon: RefreshCw,
    q: 'What if my laptop dies or I get a new one?',
    a: "Your licence is tied to your account, not the device. Sign in on your new laptop and you're back. You can be active on up to 5 devices at a time and free a slot anytime from Settings → License.",
  },
  {
    icon: Laptop,
    q: 'How many devices can I use?',
    a: `Up to ${DEVICE_LIMIT} active devices per account. That's typically a desktop, a laptop, a backup machine, plus iPad and phone for the mobile PWA.`,
  },
  {
    icon: CreditCard,
    q: 'Do you offer refunds?',
    a: "Yes — 14-day no-questions-asked refunds on lifetime purchases. The 30-day free trial is more than enough to know if the app fits your workflow, so we rarely need to invoke it.",
  },
  {
    icon: ShieldCheck,
    q: 'What if you go out of business?',
    a: "The app is open source. Your data is local SQLite — you can keep using the version you have indefinitely, export everything to standard formats (BibTeX, DOCX, CSV) any time, and the community can keep building on the codebase.",
  },
  {
    icon: HelpCircle,
    q: 'Is the trial limited in any way?',
    a: 'No. The 30-day trial unlocks every module: Library, Reader, Statistics, Meta-analysis, Manuscript editor, Peer Review, Submission, Mobile PWA. No credit card required.',
  },
]

export default function PricingPage() {
  return (
    <div className="py-16 sm:py-20">
      {/* Hero */}
      <section>
        <div className="container-narrow text-center">
          <span className="badge-soft">
            <Sparkles aria-hidden className="h-3.5 w-3.5" />
            Pricing
          </span>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">
            Simple pricing. No subscriptions.
          </h1>
          <p className="mt-4 max-w-2xl mx-auto text-base text-ink-muted sm:text-lg">
            One price, paid once. Includes every module and every future update.
            Try free for 30 days — no card required.
          </p>
        </div>
      </section>

      {/* Pricing cards */}
      <section className="mt-12">
        <div className="container-wide">
          <div className="mx-auto grid max-w-4xl gap-6 md:grid-cols-2">
            {/* Free trial card */}
            <article
              data-testid="pricing-card-trial"
              className="surface-card flex flex-col"
            >
              <header>
                <h2 className="text-xl font-semibold">Free trial</h2>
                <p className="mt-1 text-sm text-ink-muted">
                  Everything, for 30 days.
                </p>
              </header>
              <div className="mt-6 flex items-baseline gap-1">
                <span className="text-5xl font-semibold tracking-tight">$0</span>
                <span className="text-sm text-ink-muted">/ {TRIAL_DAYS} days</span>
              </div>
              <ul className="mt-6 space-y-3 text-sm text-ink-muted">
                <li className="flex items-start gap-2">
                  <Check
                    aria-hidden
                    className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600"
                  />
                  All eight modules unlocked
                </li>
                <li className="flex items-start gap-2">
                  <Check
                    aria-hidden
                    className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600"
                  />
                  No credit card required
                </li>
                <li className="flex items-start gap-2">
                  <Check
                    aria-hidden
                    className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600"
                  />
                  Upgrade any time during or after the trial
                </li>
                <li className="flex items-start gap-2">
                  <Check
                    aria-hidden
                    className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600"
                  />
                  Your data is yours — export at any time
                </li>
              </ul>
              <Link
                to="/signup"
                className="btn-secondary mt-auto pt-6"
                data-testid="pricing-trial-cta"
              >
                Start free trial
                <ArrowRight aria-hidden className="h-4 w-4" />
              </Link>
            </article>

            {/* Lifetime card */}
            <article
              data-testid="pricing-card-lifetime"
              className="surface-card flex flex-col ring-2 ring-accent ring-offset-2 ring-offset-workspace"
            >
              <header className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold">Lifetime</h2>
                  <p className="mt-1 text-sm text-ink-muted">
                    Pay once. Use forever.
                  </p>
                </div>
                <span className="badge-soft">Most popular</span>
              </header>
              <div className="mt-6 flex items-baseline gap-1">
                <span className="text-5xl font-semibold tracking-tight">
                  ${LIFETIME_PRICE_USD}
                </span>
                <span className="text-sm text-ink-muted">one-time</span>
              </div>
              <ul className="mt-6 space-y-3 text-sm text-ink-muted">
                <li className="flex items-start gap-2">
                  <Check
                    aria-hidden
                    className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600"
                  />
                  Everything in the trial
                </li>
                <li className="flex items-start gap-2">
                  <Check
                    aria-hidden
                    className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600"
                  />
                  All future modules and updates included
                </li>
                <li className="flex items-start gap-2">
                  <Check
                    aria-hidden
                    className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600"
                  />
                  Up to {DEVICE_LIMIT} active devices
                </li>
                <li className="flex items-start gap-2">
                  <Check
                    aria-hidden
                    className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600"
                  />
                  14-day refund, no questions asked
                </li>
                <li className="flex items-start gap-2">
                  <Check
                    aria-hidden
                    className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600"
                  />
                  Pay with card or PayPal (via Lemon Squeezy)
                </li>
              </ul>
              <a
                href={LEMON_SQUEEZY_CHECKOUT_URL}
                target="_blank"
                rel="noreferrer"
                className="btn-primary mt-auto pt-6"
                data-testid="pricing-lifetime-cta"
              >
                Buy now — ${LIFETIME_PRICE_USD}
                <ArrowRight aria-hidden className="h-4 w-4" />
              </a>
            </article>
          </div>
        </div>
      </section>

      {/* Why $29 section */}
      <section className="mt-20">
        <div className="container-wide">
          <div className="mx-auto max-w-3xl">
            <h2 className="text-3xl font-semibold tracking-tight">
              Why ${LIFETIME_PRICE_USD}?
            </h2>
            <p className="mt-4 text-base leading-relaxed text-ink-muted">
              Academic tools are absurdly expensive. A junior clinician
              writing their first paper shouldn&rsquo;t need to budget hundreds
              of dollars across four separate apps just to get a manuscript
              into the journal. ${LIFETIME_PRICE_USD} is roughly{' '}
              <em>one month of a Zotero Pro subscription</em>, but you only pay
              it once, and it covers every part of the workflow.
            </p>
            <div className="mt-8 overflow-hidden rounded-2xl border border-slate-200 bg-white">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-ink-soft">
                  <tr>
                    <th className="px-4 py-3">Tool</th>
                    <th className="px-4 py-3">Cost</th>
                    <th className="px-4 py-3">What you get</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {COMPARISON.map((row) => (
                    <tr key={row.product}>
                      <td className="px-4 py-3 font-medium text-ink">
                        {row.product}
                      </td>
                      <td className="px-4 py-3 text-ink-muted">{row.price}</td>
                      <td className="px-4 py-3 text-ink-muted">{row.note}</td>
                    </tr>
                  ))}
                  <tr className="bg-accent-tint/40">
                    <td className="px-4 py-3 font-semibold text-ink">
                      Research Assistant
                    </td>
                    <td className="px-4 py-3 font-semibold text-ink">
                      ${LIFETIME_PRICE_USD} once
                    </td>
                    <td className="px-4 py-3 text-ink">
                      All eight modules — library, reader, stats,
                      meta-analysis, editor, peer review, submission, mobile.
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* What's included */}
      <section className="mt-20">
        <div className="container-wide">
          <div className="mx-auto max-w-3xl">
            <h2 className="text-3xl font-semibold tracking-tight">
              What&rsquo;s included
            </h2>
            <p className="mt-4 text-base text-ink-muted">
              Both the trial and the lifetime licence unlock every module.
            </p>
            <ul className="mt-8 grid gap-3 sm:grid-cols-2">
              {INCLUDED_FEATURES.map((feature) => (
                <li
                  key={feature}
                  className="flex items-start gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-ink"
                >
                  <Check
                    aria-hidden
                    className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600"
                  />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* FAQ-lite */}
      <section className="mt-20">
        <div className="container-wide">
          <div className="mx-auto max-w-3xl">
            <h2 className="text-3xl font-semibold tracking-tight">
              Before you buy
            </h2>
            <dl className="mt-8 space-y-6">
              {FAQ.map((item) => {
                const Icon = item.icon
                return (
                  <div
                    key={item.q}
                    className="rounded-2xl border border-slate-200 bg-white p-5"
                  >
                    <dt className="flex items-start gap-3 text-base font-semibold text-ink">
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent-tint text-accent">
                        <Icon aria-hidden className="h-4 w-4" />
                      </span>
                      {item.q}
                    </dt>
                    <dd className="mt-2 pl-12 text-sm leading-relaxed text-ink-muted">
                      {item.a}
                    </dd>
                  </div>
                )
              })}
            </dl>
          </div>
        </div>
      </section>

      {/* Final CTA strip */}
      <section className="mt-20">
        <div className="container-narrow rounded-3xl bg-sidebar px-8 py-12 text-center text-sidebar-foreground shadow-card sm:px-12">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Try it free for {TRIAL_DAYS} days.
          </h2>
          <p className="mt-3 text-base text-white/70">
            Decide later. ${LIFETIME_PRICE_USD} once, lifetime updates.
          </p>
          <div className="mt-7 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              to="/signup"
              className="btn-primary !bg-white !text-ink !shadow-none"
            >
              Start free trial
            </Link>
            <a
              href={LEMON_SQUEEZY_CHECKOUT_URL}
              target="_blank"
              rel="noreferrer"
              className="btn-secondary !border-white/20 !bg-white/10 !text-white hover:!bg-white/20"
            >
              Buy lifetime — ${LIFETIME_PRICE_USD}
            </a>
          </div>
        </div>
      </section>
    </div>
  )
}
