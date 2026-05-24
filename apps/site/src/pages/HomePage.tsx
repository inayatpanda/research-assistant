import { Link } from 'react-router-dom'
import { ArrowRight, Sparkles, ShieldCheck } from 'lucide-react'

import { AnimatedHero } from '@/components/AnimatedHero'
import { TrustStrip } from '@/components/TrustStrip'
import { HowItWorks } from '@/components/HowItWorks'
import { ArchitectureDiagram } from '@/components/ArchitectureDiagram'
import { FeatureSection } from '@/components/FeatureSection'
import { FeatureShowcase } from '@/components/FeatureShowcase'
import { RevealOnScroll } from '@/components/RevealOnScroll'
import { StatCounter } from '@/components/StatCounter'
import { HomeFaqAccordion } from '@/components/AccordionSection'
import { gradient } from '@/lib/brandTokens'
import {
  LEMON_SQUEEZY_CHECKOUT_URL,
  LIFETIME_PRICE_USD,
  TRIAL_DAYS,
} from '@/lib/licenseApi'

/**
 * Home page — Phase v0.3 motion-graphics rebuild.
 *
 * Top-to-bottom narrative:
 *
 *   1. AnimatedHero — animated radial gradient + word-by-word fade-up
 *      headline + slide-in screenshot.
 *   2. FeatureShowcase — interactive auto-rotating tabs (Library →
 *      Submission) with a faux-browser screenshot frame.
 *   3. TrustStrip — four short signals (clinician-built, open source,
 *      no telemetry, no subscription).
 *   4. HowItWorks — 3-step explainer (wrapped in RevealOnScroll).
 *   5. StatCounter — five at-a-glance numbers that count up when the
 *      row scrolls into view.
 *   6. Seven FeatureSection blocks (each wrapped in RevealOnScroll).
 *   7. ArchitectureDiagram (wrapped in RevealOnScroll).
 *   8. HomeFaqAccordion — animated FAQ accordion (NEW).
 *   9. Pricing teaser + Closing CTA (each wrapped in RevealOnScroll).
 *
 * Every animated piece honours `prefers-reduced-motion`; on jsdom the
 * IntersectionObserver shim returns false but the RevealOnScroll
 * wrapper still renders children, so existing structure tests keep
 * passing.
 */
export default function HomePage() {
  return (
    <div>
      <AnimatedHero />

      {/* Interactive auto-rotating showcase — desktop only. On mobile the
          7 feature deep-dive sections further down already cover the same
          ground in a scroll-friendly format, and the showcase's
          tab-+-screenshot layout takes too much vertical real estate. */}
      <div className="hidden lg:block">
        <FeatureShowcase />
      </div>

      <TrustStrip />

      <RevealOnScroll>
        <HowItWorks />
      </RevealOnScroll>

      <StatCounter />

      {/* Anchor for the hero's "See features" secondary CTA. */}
      <div id="features" aria-hidden />

      <RevealOnScroll>
        <FeatureSection
          id="library"
          eyebrow="Library"
          title="One library that follows the manuscript."
          body={
            <>
              Import from DOI, PubMed, RIS or BibTeX. The library dedupes
              automatically, merges duplicates, and stays attached to the
              project so every citation you drop into the editor resolves on
              the first try.
            </>
          }
          bullets={[
            'DOI lookup via Crossref + OpenAlex with PubMed E-utilities fallback.',
            'Drop a .ris or .bib export — instant dedup against existing entries.',
            'Drag in a PDF or Word doc to attach the file and parse metadata.',
          ]}
          side="right"
          screenshots={[
            {
              src: '/screenshots/library.png',
              alt: 'Library view with imported articles for an ACL systematic review',
              urlLabel: 'manuscripts.local · Library',
            },
          ]}
        />
      </RevealOnScroll>

      <RevealOnScroll>
        <FeatureSection
          id="reader"
          eyebrow="Reader"
          title="Read like a reviewer. Highlight like a clinician."
          body={
            <>
              Open any PDF in the project and mark it up with four
              colour-coded highlights — Introduction, Methods, Results,
              Discussion. Generate an AI paraphrase per paragraph without
              ever leaving the page.
            </>
          }
          bullets={[
            'Four highlight colours mapped to manuscript sections.',
            'Inline AI paraphrasing per paragraph — Gemini, Claude or OpenAI.',
            'Per-paragraph notes that survive when you re-open the PDF.',
          ]}
          side="left"
          screenshots={[
            {
              src: '/screenshots/reader.png',
              alt: 'PDF reader with the highlight colour picker and the highlights panel',
              urlLabel: 'manuscripts.local · Reader',
            },
          ]}
          tint="emerald"
        />
      </RevealOnScroll>

      <RevealOnScroll>
        <FeatureSection
          id="manuscript"
          eyebrow="Manuscript editor"
          title="A clinical-research-shaped editor."
          body={
            <>
              TipTap-powered editor with @-citations, native tables, figure
              blocks and an ordered bibliography panel. Citations stay in
              sync with the library; tables and figures move with the section
              they belong to.
            </>
          }
          bullets={[
            '@-citation picker resolves against the project library.',
            'Native tables, figures, callouts and equations.',
            'Bibliography renders in Vancouver, AMA, NEJM, BJJ and more.',
          ]}
          side="right"
          screenshots={[
            {
              src: '/screenshots/manuscript.png',
              alt: 'Manuscript editor showing the Introduction section with citations and figures',
              urlLabel: 'manuscripts.local · Manuscript · Introduction',
            },
          ]}
        />
      </RevealOnScroll>

      <RevealOnScroll>
        <FeatureSection
          id="statistics"
          eyebrow="Statistics & meta-analysis"
          title="From t-test to forest plot, without leaving the app."
          body={
            <>
              Upload a masterchart, let the app recommend a test, run it, and
              push the interpretation straight into your Results section.
              For systematic reviews, pool effects with a random-effects
              model and export forest + funnel plots that match journal
              style.
            </>
          }
          bullets={[
            'Independent t, ANOVA, chi-square, regression, GEE, survival, PSM.',
            'Random-effects meta-analysis with subgroup, leave-one-out, GRADE.',
            'Diagnostics + AI interpretation for every analysis you run.',
          ]}
          side="left"
          screenshots={[
            {
              src: '/screenshots/statistics.png',
              alt: 'Statistics page with a masterchart preview and an independent t-test recommendation',
              urlLabel: 'manuscripts.local · Statistics',
            },
            {
              src: '/screenshots/meta-analysis.png',
              alt: 'Meta-analysis forest plot of six included studies',
              urlLabel: 'manuscripts.local · Meta-analysis',
            },
          ]}
          tint="ai"
        />
      </RevealOnScroll>

      <RevealOnScroll>
        <FeatureSection
          id="peer-review"
          eyebrow="Peer Review"
          title="A structured AI critique before the reviewers see it."
          body={
            <>
              Send your manuscript (or any uploaded PDF) through the AI peer
              reviewer and get a structured critique — overall impression,
              strengths, major issues, statistical concerns, reporting,
              references, suggestions for improvement.
            </>
          }
          bullets={[
            'Section-by-section critique, not a generic vibe-check.',
            'Highlights statistical and reporting gaps using PRISMA / CONSORT.',
            'Save reviews to compare drafts over time.',
          ]}
          side="right"
          screenshots={[
            {
              src: '/screenshots/peer-review.png',
              alt: 'Peer review page with collapsible sections of an AI critique',
              urlLabel: 'manuscripts.local · Peer Review',
            },
          ]}
          tint="ai"
        />
      </RevealOnScroll>

      <RevealOnScroll>
        <FeatureSection
          id="submission"
          eyebrow="Submission"
          title="The whole submission packet, in one zip."
          body={
            <>
              Cover letter editor with novelty bullets, journal target,
              reviewer responses, and a one-click export that bundles the
              DOCX manuscript, figures, tables and supplementary files into
              a single submission package per journal style.
            </>
          }
          bullets={[
            'Cover-letter template with @-references and per-journal style.',
            'Reviewer-response builder with side-by-side critique view.',
            'Submission zip — DOCX + figures + tables + supplementary, ready to upload.',
          ]}
          side="left"
          screenshots={[
            {
              src: '/screenshots/submission.png',
              alt: 'Submission page with a populated cover letter for an NEJM submission',
              urlLabel: 'manuscripts.local · Submission',
            },
          ]}
          tint="amber"
        />
      </RevealOnScroll>

      <RevealOnScroll>
        <FeatureSection
          id="mobile"
          eyebrow="Mobile PWA"
          title="Read on the ward. Highlight on the bus."
          body={
            <>
              The mobile shell talks to your laptop over your private
              Tailscale network. Read library articles, run a quick stats
              wizard, capture peer-review notes — and pick the work up on
              your Mac when you get home.
            </>
          }
          bullets={[
            'Library + Reader sized for one-handed phone use.',
            'Stats wizard runs the same analyses as the desktop app.',
            'Installs as a PWA on iPad / iPhone — no app store, no review queue.',
          ]}
          side="right"
          screenshots={[
            {
              src: '/screenshots/mobile-library.png',
              alt: 'Mobile library list on iPhone',
              mobile: true,
            },
            {
              src: '/screenshots/mobile-reader.png',
              alt: 'Mobile article reader with a highlighted abstract',
              mobile: true,
            },
          ]}
        />
      </RevealOnScroll>

      {/* Architecture diagram block */}
      <RevealOnScroll>
        <section
          className="border-b border-slate-200 bg-slate-50/70 py-20 sm:py-24"
          aria-labelledby="architecture-heading"
        >
          <div className="container-wide">
            <div className="mx-auto max-w-2xl text-center">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
                Architecture
              </p>
              <h2
                id="architecture-heading"
                className="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-4xl"
              >
                Your data lives on your hardware.
              </h2>
              <p className="mt-3 text-base text-ink-muted">
                Nothing in the diagram below is a cloud service. Every arrow is a
                direct connection over your private Tailscale network.
              </p>
            </div>
            <div className="mx-auto mt-12 max-w-4xl">
              <ArchitectureDiagram />
            </div>
          </div>
        </section>
      </RevealOnScroll>

      {/* Accordion FAQ — NEW */}
      <RevealOnScroll>
        <HomeFaqAccordion />
      </RevealOnScroll>

      {/* Pricing teaser */}
      <RevealOnScroll>
        <section className="py-20 sm:py-24" aria-labelledby="pricing-teaser-heading">
          <div className="container-wide">
            <div className="mx-auto max-w-2xl text-center">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
                Pricing
              </p>
              <h2
                id="pricing-teaser-heading"
                className="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-4xl"
              >
                Free for {TRIAL_DAYS} days. ${LIFETIME_PRICE_USD} once after that.
              </h2>
            </div>
            <div className="mx-auto mt-12 grid max-w-3xl gap-6 sm:grid-cols-2">
              <article className="surface-card flex flex-col">
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-accent">
                  Free trial
                </div>
                <div className="mt-3 text-3xl font-semibold tracking-tight text-ink">
                  $0
                </div>
                <div className="text-xs text-ink-soft">for {TRIAL_DAYS} days</div>
                <p className="mt-4 text-sm leading-relaxed text-ink-muted">
                  Full feature access, no credit card, no install hurdle. The
                  trial ends quietly and your local data stays exactly where it
                  is.
                </p>
                <Link to="/signup" className="btn-primary mt-6 self-start">
                  Start free trial
                  <ArrowRight aria-hidden className="h-4 w-4" />
                </Link>
              </article>
              <article
                className="relative flex flex-col overflow-hidden rounded-2xl border border-accent/30 bg-white p-6 shadow-card"
                style={{
                  backgroundImage:
                    'radial-gradient(120% 100% at 100% 0%, rgba(37,99,235,0.08) 0%, rgba(255,255,255,0) 70%)',
                }}
              >
                <div className="absolute right-4 top-4">
                  <span className="inline-flex items-center gap-1 rounded-full bg-accent px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-white">
                    <Sparkles aria-hidden className="h-3 w-3" />
                    Best value
                  </span>
                </div>
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-accent">
                  Lifetime
                </div>
                <div className="mt-3 text-3xl font-semibold tracking-tight text-ink">
                  ${LIFETIME_PRICE_USD}
                </div>
                <div className="text-xs text-ink-soft">one-time payment</div>
                <p className="mt-4 text-sm leading-relaxed text-ink-muted">
                  Every feature, every future update, on every device you own.
                  No subscription, no usage limits, no surprise renewals.
                </p>
                <div className="mt-6 flex flex-wrap gap-2">
                  <a
                    href={LEMON_SQUEEZY_CHECKOUT_URL}
                    className="btn-primary"
                    target="_blank"
                    rel="noreferrer"
                  >
                    Buy lifetime
                  </a>
                  <Link to="/pricing" className="btn-secondary">
                    See pricing
                  </Link>
                </div>
              </article>
            </div>
          </div>
        </section>
      </RevealOnScroll>

      {/* Closing CTA */}
      <RevealOnScroll>
        <section className="pb-24">
          <div
            className="container-narrow relative overflow-hidden rounded-3xl px-10 py-16 text-center text-sidebar-foreground shadow-card"
            style={{ background: gradient.inkCta }}
          >
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0"
              style={{
                background:
                  'radial-gradient(60% 80% at 50% 0%, rgba(124,58,237,0.25) 0%, rgba(37,99,235,0.12) 35%, transparent 70%)',
              }}
            />
            <div className="relative">
              <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium text-white/80">
                <ShieldCheck aria-hidden className="h-3.5 w-3.5" />
                Free {TRIAL_DAYS}-day trial · No credit card · ${LIFETIME_PRICE_USD} lifetime upgrade
              </span>
              <h2 className="mt-6 text-3xl font-semibold tracking-tight sm:text-4xl">
                Spend your weekend writing, not stitching tools together.
              </h2>
              <p className="mx-auto mt-3 max-w-xl text-base text-white/70">
                One app for the library, the reader, the editor, the stats and
                the submission packet. Local, private, fast.
              </p>
              <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
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
          </div>
        </section>
      </RevealOnScroll>
    </div>
  )
}
