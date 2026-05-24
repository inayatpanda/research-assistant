import { useEffect, useRef, useState } from 'react'
import { motion, useInView, useReducedMotion } from 'framer-motion'

/**
 * Phase v0.3 — Stat counter row.
 *
 * Five at-a-glance numbers about the product, each counting up from 0
 * to the target when the row enters the viewport. With
 * `prefers-reduced-motion` we render the final number immediately and
 * skip the animation.
 *
 * Each counter has an optional suffix (e.g. "+") so 60+ reads as
 * "60+" once the count finishes.
 */

interface StatItem {
  /** The target numeric value. */
  value: number
  /** Optional suffix appended after the value (e.g. "+"). */
  suffix?: string
  /** Short heading underneath the number. */
  label: string
}

const STATS: readonly StatItem[] = [
  { value: 27, label: 'Statistical tests built in' },
  { value: 12, label: 'Reporting checklists' },
  { value: 60, suffix: '+', label: 'Curated reference entries' },
  { value: 3, label: 'Platforms (Mac, Win, Linux)' },
  { value: 0, label: 'Cloud dependencies' },
] as const

const COUNT_DURATION_MS = 3000

function easeOutCubic(t: number) {
  return 1 - Math.pow(1 - t, 3)
}

interface CounterProps {
  target: number
  suffix?: string
  active: boolean
}

function Counter({ target, suffix, active }: CounterProps) {
  const reduceMotion = useReducedMotion()
  const [display, setDisplay] = useState(active || reduceMotion ? target : 0)

  useEffect(() => {
    if (reduceMotion) {
      setDisplay(target)
      return
    }
    if (!active) return
    if (target === 0) {
      setDisplay(0)
      return
    }
    let raf = 0
    const start = performance.now()
    function tick(now: number) {
      const elapsed = now - start
      const t = Math.min(1, elapsed / COUNT_DURATION_MS)
      const eased = easeOutCubic(t)
      setDisplay(Math.round(eased * target))
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [active, target, reduceMotion])

  return (
    <span>
      <span aria-hidden>
        {display}
        {suffix ?? ''}
      </span>
      <span className="sr-only" aria-live="polite">
        {display === target ? `${target}${suffix ?? ''}` : ''}
      </span>
    </span>
  )
}

export function StatCounter() {
  const ref = useRef<HTMLDListElement>(null)
  const inView = useInView(ref, { once: true, margin: '0px 0px -10% 0px' })
  const reduceMotion = useReducedMotion()
  const active = inView || reduceMotion === true

  return (
    <section
      className="border-b border-slate-200 bg-slate-50/40 py-16"
      aria-labelledby="stat-counter-heading"
      data-testid="stat-counter"
    >
      <div className="container-wide">
        <h2 id="stat-counter-heading" className="sr-only">
          Research Assistant by the numbers
        </h2>
        <motion.dl
          ref={ref}
          className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-3 lg:grid-cols-5"
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={inView || reduceMotion ? { opacity: 1 } : undefined}
          transition={{ duration: 0.5 }}
        >
          {STATS.map((stat) => (
            <div
              key={stat.label}
              className="text-center"
              data-testid={`stat-${stat.value}`}
            >
              <dt className="sr-only">{stat.label}</dt>
              <dd>
                <span
                  className="block text-4xl font-semibold tracking-tight text-ink sm:text-5xl"
                  style={{
                    backgroundImage:
                      'linear-gradient(135deg, #0F1117 0%, #2563EB 100%)',
                    WebkitBackgroundClip: 'text',
                    backgroundClip: 'text',
                    color: 'transparent',
                  }}
                >
                  <Counter target={stat.value} suffix={stat.suffix} active={active} />
                </span>
                <span
                  className="mt-2 block text-xs font-medium uppercase tracking-[0.14em] text-ink-soft"
                  aria-hidden
                >
                  {stat.label}
                </span>
              </dd>
            </div>
          ))}
        </motion.dl>
      </div>
    </section>
  )
}
