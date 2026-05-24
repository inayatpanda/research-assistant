import { useEffect, useRef, useState, type ComponentType, type KeyboardEvent } from 'react'
import {
  AnimatePresence,
  motion,
  useReducedMotion,
} from 'framer-motion'
import {
  Library,
  BookOpen,
  FileText,
  BarChart3,
  GitBranch,
  MessageSquareWarning,
  Send,
} from 'lucide-react'

/**
 * Phase v0.3 — Interactive feature showcase.
 *
 * Sits directly below the hero. Auto-rotates through the seven core
 * app surfaces (Library, Reader, Manuscript, Statistics, Meta-analysis,
 * Peer Review, Submission). Each tab swaps the browser-frame screenshot
 * with a crossfade and updates the fake URL bar.
 *
 * Behaviour:
 *   - Default: rotates every 5 s.
 *   - Hover over the showcase: pause auto-rotation.
 *   - Click any tab: select manually + STOP auto-rotation entirely
 *     (we don't want to fight the user's pick).
 *   - prefers-reduced-motion: skip the crossfade + disable auto-rotate.
 *
 * Accessibility:
 *   - The tabs sit inside a `role="tablist"` with proper aria-selected /
 *     aria-controls wiring.
 *   - Arrow Up / Arrow Down (and Left / Right) move focus through tabs.
 *   - The screenshot region is `role="tabpanel"` for the selected tab.
 */

interface ShowcaseTab {
  id: string
  title: string
  description: string
  icon: ComponentType<{ className?: string; 'aria-hidden'?: boolean }>
  screenshot: string
  alt: string
  urlLabel: string
}

const TABS: readonly ShowcaseTab[] = [
  {
    id: 'library',
    title: 'Library',
    description: 'Import, dedup, organise references',
    icon: Library,
    screenshot: '/screenshots/library.png',
    alt: 'Library view with imported articles for an ACL systematic review',
    urlLabel: 'manuscripts.local/projects/acl-review/library',
  },
  {
    id: 'reader',
    title: 'Reader',
    description: 'Colour-coded highlights + AI paraphrase',
    icon: BookOpen,
    screenshot: '/screenshots/reader.png',
    alt: 'PDF reader with highlight colour picker and the highlights panel',
    urlLabel: 'manuscripts.local/projects/acl-review/reader',
  },
  {
    id: 'manuscript',
    title: 'Manuscript',
    description: '@-citation editor with tables and figures',
    icon: FileText,
    screenshot: '/screenshots/manuscript.png',
    alt: 'Manuscript editor showing the Introduction section with citations and figures',
    urlLabel: 'manuscripts.local/projects/acl-review/manuscript',
  },
  {
    id: 'statistics',
    title: 'Statistics',
    description: '27 stat tests with AI interpretation',
    icon: BarChart3,
    screenshot: '/screenshots/statistics.png',
    alt: 'Statistics page with a masterchart preview and t-test recommendation',
    urlLabel: 'manuscripts.local/projects/acl-review/statistics',
  },
  {
    id: 'meta-analysis',
    title: 'Meta-analysis',
    description: 'Forest plots, funnel plots, GRADE',
    icon: GitBranch,
    screenshot: '/screenshots/meta-analysis.png',
    alt: 'Meta-analysis forest plot of six included studies',
    urlLabel: 'manuscripts.local/projects/acl-review/meta-analysis',
  },
  {
    id: 'peer-review',
    title: 'Peer Review',
    description: 'Structured AI critique before submission',
    icon: MessageSquareWarning,
    screenshot: '/screenshots/peer-review.png',
    alt: 'Peer review page with collapsible sections of an AI critique',
    urlLabel: 'manuscripts.local/projects/acl-review/peer-review',
  },
  {
    id: 'submission',
    title: 'Submission',
    description: 'Cover letters + one-click zip packet',
    icon: Send,
    screenshot: '/screenshots/submission.png',
    alt: 'Submission page with a populated cover letter for an NEJM submission',
    urlLabel: 'manuscripts.local/projects/acl-review/submission',
  },
] as const

const AUTO_ROTATE_MS = 5000

export function FeatureShowcase() {
  const reduceMotion = useReducedMotion()
  const [activeIdx, setActiveIdx] = useState(0)
  const [isPaused, setIsPaused] = useState(false)
  const [manualSelect, setManualSelect] = useState(false)
  // Progress ticks 0 → 1 over AUTO_ROTATE_MS so the bottom bar can fill.
  const [progress, setProgress] = useState(0)
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([])

  const active = TABS[activeIdx]

  // Auto-rotation timer + progress bar driver.
  //
  // We tick at 60 ms and count ticks rather than reading Date.now() —
  // counting plays nicely with vitest fake timers (which can mock
  // setInterval without mocking Date).
  useEffect(() => {
    if (reduceMotion || manualSelect || isPaused) return
    const TICK_MS = 60
    const totalTicks = Math.ceil(AUTO_ROTATE_MS / TICK_MS)
    let ticks = 0
    setProgress(0)
    const handle = window.setInterval(() => {
      ticks += 1
      const pct = Math.min(1, ticks / totalTicks)
      setProgress(pct)
      if (ticks >= totalTicks) {
        setActiveIdx((i) => (i + 1) % TABS.length)
      }
    }, TICK_MS)
    return () => window.clearInterval(handle)
  }, [activeIdx, reduceMotion, manualSelect, isPaused])

  function selectTab(idx: number) {
    setActiveIdx(idx)
    setManualSelect(true)
    setProgress(0)
  }

  function onTabKey(e: KeyboardEvent<HTMLButtonElement>, idx: number) {
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
      e.preventDefault()
      const next = (idx + 1) % TABS.length
      tabRefs.current[next]?.focus()
      selectTab(next)
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
      e.preventDefault()
      const prev = (idx - 1 + TABS.length) % TABS.length
      tabRefs.current[prev]?.focus()
      selectTab(prev)
    } else if (e.key === 'Home') {
      e.preventDefault()
      tabRefs.current[0]?.focus()
      selectTab(0)
    } else if (e.key === 'End') {
      e.preventDefault()
      const last = TABS.length - 1
      tabRefs.current[last]?.focus()
      selectTab(last)
    }
  }

  return (
    <section
      id="showcase"
      data-testid="feature-showcase"
      aria-labelledby="showcase-heading"
      className="border-b border-slate-200 bg-gradient-to-b from-white to-slate-50/60 py-16 sm:py-20"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      <div className="container-wide">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
            One app, seven surfaces
          </p>
          <h2
            id="showcase-heading"
            className="mt-3 text-3xl font-semibold tracking-tight text-ink sm:text-4xl"
          >
            See the whole workflow without scrolling.
          </h2>
          <p className="mt-3 text-base text-ink-muted">
            Click a tab to jump in. Otherwise we'll walk you through the seven
            screens that make up a Research Assistant project.
          </p>
        </div>

        <div className="mt-10 grid gap-6 lg:grid-cols-12 lg:gap-8">
          {/* Tabs — vertical on lg+, horizontal scrollable chips on mobile */}
          <div
            role="tablist"
            aria-orientation="vertical"
            aria-label="Feature surfaces"
            data-testid="showcase-tablist"
            className="lg:col-span-3"
          >
            <div className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
              {TABS.map((tab, idx) => {
                const isActive = idx === activeIdx
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    ref={(el) => {
                      tabRefs.current[idx] = el
                    }}
                    role="tab"
                    type="button"
                    id={`showcase-tab-${tab.id}`}
                    aria-selected={isActive}
                    aria-controls={`showcase-panel-${tab.id}`}
                    tabIndex={isActive ? 0 : -1}
                    onClick={() => selectTab(idx)}
                    onKeyDown={(e) => onTabKey(e, idx)}
                    data-testid={`showcase-tab-${tab.id}`}
                    data-active={isActive}
                    className={[
                      'group flex shrink-0 items-center gap-2 rounded-xl border px-3 py-2 text-left transition-all',
                      // Mobile: compact pill (icon + title only). lg+: full card with description.
                      'min-w-0 lg:min-w-0 lg:items-start lg:gap-3 lg:px-4 lg:py-3',
                      isActive
                        ? 'border-accent/30 bg-white shadow-card lg:border-l-4 lg:border-l-accent lg:scale-[1.02]'
                        : 'border-transparent bg-white/40 hover:-translate-y-0.5 hover:bg-white hover:shadow-sm',
                      'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent',
                    ].join(' ')}
                  >
                    <span
                      className={[
                        'flex h-8 w-8 lg:h-9 lg:w-9 shrink-0 items-center justify-center rounded-lg transition-colors',
                        isActive
                          ? 'bg-accent-tint text-accent'
                          : 'bg-slate-100 text-ink-soft group-hover:bg-accent-tint group-hover:text-accent',
                      ].join(' ')}
                    >
                      <Icon aria-hidden className="h-4 w-4" />
                    </span>
                    <span className="min-w-0">
                      <span
                        className={[
                          'block text-[13px] lg:text-sm font-semibold leading-tight transition-colors whitespace-nowrap lg:whitespace-normal',
                          isActive ? 'text-ink' : 'text-ink-muted',
                        ].join(' ')}
                      >
                        {tab.title}
                      </span>
                      {/* Description only on lg+ — mobile keeps chips compact */}
                      <span className="mt-0.5 hidden lg:block text-xs leading-snug text-ink-soft">
                        {tab.description}
                      </span>
                    </span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Screenshot panel */}
          <div className="lg:col-span-9">
            <div
              role="tabpanel"
              id={`showcase-panel-${active.id}`}
              aria-labelledby={`showcase-tab-${active.id}`}
              data-testid="showcase-panel"
              className="relative"
            >
              <div
                aria-hidden
                className="pointer-events-none absolute -inset-6 -z-10 rounded-[2rem] opacity-60 blur-3xl"
                style={{
                  background:
                    'linear-gradient(120deg, rgba(37,99,235,0.16) 0%, rgba(124,58,237,0.14) 60%, rgba(255,255,255,0) 100%)',
                }}
              />

              <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-2xl shadow-slate-900/10">
                {/* Browser chrome */}
                <div className="flex items-center gap-2 border-b border-slate-200/80 bg-slate-50 px-3 py-2">
                  <span className="h-3 w-3 rounded-full bg-rose-400/90" aria-hidden />
                  <span className="h-3 w-3 rounded-full bg-amber-300/90" aria-hidden />
                  <span className="h-3 w-3 rounded-full bg-emerald-400/90" aria-hidden />
                  <div
                    className="ml-3 flex-1 truncate rounded-md bg-white/80 px-3 py-1 text-[11px] font-mono text-ink-soft shadow-inner"
                    data-testid="showcase-url-bar"
                    aria-hidden
                  >
                    {active.urlLabel}
                  </div>
                </div>

                {/* Image with crossfade */}
                <div className="relative aspect-[1440/900] bg-slate-50">
                  {reduceMotion ? (
                    <img
                      src={active.screenshot}
                      alt={active.alt}
                      data-testid="showcase-screenshot"
                      data-active-id={active.id}
                      loading="eager"
                      decoding="async"
                      className="absolute inset-0 block h-full w-full object-cover object-top"
                    />
                  ) : (
                    <AnimatePresence mode="wait" initial={false}>
                      <motion.img
                        key={active.id}
                        src={active.screenshot}
                        alt={active.alt}
                        data-testid="showcase-screenshot"
                        data-active-id={active.id}
                        loading="eager"
                        decoding="async"
                        initial={{ opacity: 0, scale: 0.98 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 1.01 }}
                        transition={{
                          duration: 0.4,
                          ease: [0.16, 1, 0.3, 1],
                        }}
                        className="absolute inset-0 block h-full w-full object-cover object-top"
                      />
                    </AnimatePresence>
                  )}
                </div>

                {/* Progress bar — only when auto-rotating */}
                <div
                  className="h-1 w-full bg-slate-100"
                  aria-hidden
                  data-testid="showcase-progress"
                >
                  <div
                    className="h-full bg-accent transition-[width] duration-100"
                    style={{
                      width: manualSelect || reduceMotion ? '0%' : `${progress * 100}%`,
                    }}
                  />
                </div>
              </div>

              {/* Status row beneath the frame */}
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-ink-soft">
                <span>
                  <span className="font-mono text-ink">
                    {String(activeIdx + 1).padStart(2, '0')}
                  </span>{' '}
                  / {String(TABS.length).padStart(2, '0')} ·{' '}
                  <span className="text-ink">{active.title}</span>
                </span>
                <span>
                  {manualSelect
                    ? 'Manual mode — pick a tab to keep exploring'
                    : reduceMotion
                      ? 'Static mode'
                      : isPaused
                        ? 'Paused — move away to resume'
                        : 'Auto-cycling every 5s'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
