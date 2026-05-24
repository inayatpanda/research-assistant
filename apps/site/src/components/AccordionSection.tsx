import { useState, type ReactNode } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import { Link } from 'react-router-dom'

/**
 * Phase v0.3 — Animated accordion section.
 *
 * Reusable accordion with framer-motion smooth height transitions and
 * a rotating chevron. Supports two modes:
 *   - `single` (default): only one item can be open at a time.
 *   - `multi`: any number can be open simultaneously.
 *
 * Each trigger is a real <button> with aria-expanded + aria-controls
 * so screen readers + keyboard users get correct semantics.
 *
 * The component itself is generic — `<AccordionSection items={...} />`.
 * The home page uses a pre-baked content set (FAQ_ITEMS) wrapped by
 * `<HomeFaqAccordion />` below.
 */

export interface AccordionItem {
  /** Stable identifier used in aria attributes + as React key. */
  id: string
  question: string
  /** Renderable answer body — can be a string or JSX. */
  answer: ReactNode
}

interface AccordionSectionProps {
  items: readonly AccordionItem[]
  /** Open-mode. Defaults to single (only one open at a time). */
  mode?: 'single' | 'multi'
  /** Optional id for testing / linking. */
  id?: string
  className?: string
}

export function AccordionSection({
  items,
  mode = 'single',
  id,
  className,
}: AccordionSectionProps) {
  const reduceMotion = useReducedMotion()
  const [openIds, setOpenIds] = useState<Set<string>>(new Set())

  function toggle(itemId: string) {
    setOpenIds((prev) => {
      const next = new Set(prev)
      if (next.has(itemId)) {
        next.delete(itemId)
      } else {
        if (mode === 'single') next.clear()
        next.add(itemId)
      }
      return next
    })
  }

  return (
    <div
      id={id}
      data-testid={id ?? 'accordion-section'}
      className={[
        'divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-white',
        className ?? '',
      ].join(' ')}
    >
      {items.map((item) => {
        const isOpen = openIds.has(item.id)
        const panelId = `acc-panel-${item.id}`
        const buttonId = `acc-btn-${item.id}`
        return (
          <div key={item.id} data-testid={`acc-item-${item.id}`}>
            <h3>
              <button
                type="button"
                id={buttonId}
                aria-expanded={isOpen}
                aria-controls={panelId}
                onClick={() => toggle(item.id)}
                data-testid={`acc-trigger-${item.id}`}
                className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left text-base font-medium text-ink transition-colors hover:bg-slate-50 hover:text-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-accent"
              >
                <span>{item.question}</span>
                <motion.span
                  aria-hidden
                  initial={false}
                  animate={{ rotate: isOpen ? 180 : 0 }}
                  transition={
                    reduceMotion
                      ? { duration: 0 }
                      : { duration: 0.25, ease: [0.16, 1, 0.3, 1] }
                  }
                  className="text-ink-soft"
                >
                  <ChevronDown className="h-5 w-5 shrink-0" />
                </motion.span>
              </button>
            </h3>
            <AnimatePresence initial={false}>
              {isOpen ? (
                <motion.div
                  key="panel"
                  id={panelId}
                  role="region"
                  aria-labelledby={buttonId}
                  data-testid={`acc-panel-${item.id}`}
                  initial={reduceMotion ? false : { height: 0, opacity: 0 }}
                  animate={
                    reduceMotion
                      ? { height: 'auto', opacity: 1 }
                      : { height: 'auto', opacity: 1 }
                  }
                  exit={
                    reduceMotion
                      ? { height: 0, opacity: 0 }
                      : { height: 0, opacity: 0 }
                  }
                  transition={
                    reduceMotion
                      ? { duration: 0 }
                      : { duration: 0.3, ease: [0.16, 1, 0.3, 1] }
                  }
                  className="overflow-hidden"
                >
                  <div className="px-6 pb-6 pr-12 text-sm leading-relaxed text-ink-muted">
                    {item.answer}
                  </div>
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>
        )
      })}
    </div>
  )
}

// -- Home page FAQ content -------------------------------------------------

const FAQ_ITEMS: readonly AccordionItem[] = [
  {
    id: 'local-first',
    question: 'Why local-first?',
    answer: (
      <p>
        Patient identifiers and unpublished manuscripts shouldn't sit in a
        third-party cloud. Local-first means your SQLite database lives on your
        Mac, you can audit every byte, and the app keeps working when your
        hospital wifi doesn't.
      </p>
    ),
  },
  {
    id: 'sync',
    question: 'How is sync different from cloud sync?',
    answer: (
      <p>
        Your Mac runs a tiny server on your private{' '}
        <Link to="/sync" className="link-soft">
          Tailscale
        </Link>{' '}
        network. Other devices (iPad, iPhone, a co-author's laptop) just open a
        URL on that network — no central server, no third-party uptime to rely
        on, no files leaving your machine.
      </p>
    ),
  },
  {
    id: 'stats',
    question: 'Which statistical tests are supported?',
    answer: (
      <p>
        27 tests out of the box: independent / paired t-tests, one-way and
        repeated-measures ANOVA, Mann–Whitney U, Wilcoxon, Kruskal–Wallis,
        chi-square, Fisher's exact, simple + multivariable linear and logistic
        regression, Cox regression, Kaplan–Meier with log-rank, propensity
        score matching, generalised estimating equations, ICC, Bland–Altman,
        Cohen's kappa, and more — plus random-effects meta-analysis with
        subgroup, leave-one-out and GRADE outputs.
      </p>
    ),
  },
  {
    id: 'import',
    question: 'Can I import from Zotero / Mendeley / EndNote?',
    answer: (
      <p>
        Yes — both RIS and BibTeX exports drop straight into the library, get
        deduped against existing entries, and stay attached to the project so
        every citation resolves. PDF attachments come along for the ride.
      </p>
    ),
  },
  {
    id: 'offline',
    question: 'Does it work offline?',
    answer: (
      <p>
        Reading, writing, running stats, and exporting do — they're entirely
        local. AI features (peer review, paraphrasing, interpretation) need
        your own API key for Gemini, Claude or OpenAI and therefore need a
        network connection.
      </p>
    ),
  },
  {
    id: 'open-source',
    question: 'Is the source code open?',
    answer: (
      <p>
        The desktop and web shells are open source on{' '}
        <a
          href="https://github.com"
          target="_blank"
          rel="noreferrer"
          className="link-soft"
        >
          GitHub
        </a>
        . You can read every line, build it from source, fork it, audit it
        before you let it near patient data — that's part of the point.
      </p>
    ),
  },
] as const

/**
 * Pre-baked FAQ accordion used on the home page. Lives here so the
 * <AccordionSection> primitive stays content-agnostic.
 */
export function HomeFaqAccordion() {
  return (
    <section
      className="border-b border-slate-100 py-20 sm:py-24"
      aria-labelledby="home-faq-heading"
      data-testid="home-faq"
    >
      <div className="container-wide">
        <div className="mx-auto grid max-w-5xl gap-10 lg:grid-cols-12 lg:items-start">
          <div className="lg:col-span-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
              Built for clinical research
            </p>
            <h2
              id="home-faq-heading"
              className="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-4xl"
            >
              Questions clinicians actually ask.
            </h2>
            <p className="mt-3 text-base text-ink-muted">
              Local-first sounds simple until you have to share a manuscript
              with a co-author on the wrong continent. Here's how we answer the
              questions that come up before anyone reaches the pricing page.
            </p>
          </div>
          <div className="lg:col-span-7">
            <AccordionSection items={FAQ_ITEMS} id="home-faq-list" />
          </div>
        </div>
      </div>
    </section>
  )
}
