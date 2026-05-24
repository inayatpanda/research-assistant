import { Link } from 'react-router-dom'
import { ArrowRight, Sparkles } from 'lucide-react'
import { motion, useReducedMotion, type Variants } from 'framer-motion'
import { ScreenshotFrame } from './ScreenshotFrame'
import { dotPattern, gradient } from '@/lib/brandTokens'
import { TRIAL_DAYS } from '@/lib/licenseApi'

/**
 * Phase v0.3 — animated hero.
 *
 * Same layout + copy as the static `<Hero />` component, but with:
 *   - a slow-drifting radial gradient backdrop (CSS keyframes, no JS)
 *   - word-by-word fade-up headline (framer-motion stagger)
 *   - subhead + CTAs fade-up with a small bounce
 *   - screenshot slides in from the right with a soft shadow
 *
 * Honours `prefers-reduced-motion`: renders identically to the static
 * hero with no transforms or opacity transitions.
 */

const HEADLINE_PRE = 'The local-first'
const HEADLINE_GRADIENT = 'manuscript tool'
const HEADLINE_POST = 'for clinical research.'

export function AnimatedHero() {
  const reduceMotion = useReducedMotion()

  // Split into tokens so each word fades up individually.
  const preWords = HEADLINE_PRE.split(' ')
  const postWords = HEADLINE_POST.split(' ')

  const containerVariants: Variants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: 0.06,
        delayChildren: 0.05,
      },
    },
  }
  const wordVariants: Variants = {
    hidden: { opacity: 0, y: 18 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] },
    },
  }
  const fadeUpVariants: Variants = {
    hidden: { opacity: 0, y: 16 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.55, ease: [0.16, 1, 0.3, 1] },
    },
  }
  const ctaVariants: Variants = {
    hidden: { opacity: 0, scale: 0.94 },
    visible: {
      opacity: 1,
      scale: 1,
      transition: { duration: 0.5, ease: [0.34, 1.56, 0.64, 1] }, // spring-y
    },
  }
  const screenshotVariants: Variants = {
    hidden: { opacity: 0, x: 40 },
    visible: {
      opacity: 1,
      x: 0,
      transition: { duration: 0.7, delay: 0.2, ease: [0.16, 1, 0.3, 1] },
    },
  }
  const flatVariants: Variants = {
    hidden: { opacity: 1 },
    visible: { opacity: 1 },
  }

  // When motion is reduced, swap all variants for instant visible state.
  const v = (variants: Variants): Variants => (reduceMotion ? flatVariants : variants)

  return (
    <section
      className="relative isolate overflow-hidden border-b border-slate-200 bg-white"
      data-testid="animated-hero"
    >
      {/* Animated radial gradient — pure CSS so it works even when JS
          animations are disabled. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{ background: gradient.heroSky }}
      />
      <div
        aria-hidden
        className={[
          'pointer-events-none absolute inset-0 -z-10',
          reduceMotion ? '' : 'animate-hero-drift',
        ].join(' ')}
        style={{
          background:
            'radial-gradient(45% 40% at 30% 30%, rgba(37,99,235,0.18) 0%, rgba(255,255,255,0) 60%), radial-gradient(40% 40% at 75% 20%, rgba(124,58,237,0.18) 0%, rgba(255,255,255,0) 60%)',
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 opacity-60"
        style={{
          backgroundImage: dotPattern,
          maskImage:
            'radial-gradient(70% 60% at 50% 30%, black 0%, transparent 100%)',
        }}
      />

      <div className="container-wide grid items-center gap-10 py-16 sm:py-20 lg:grid-cols-12 lg:gap-16 lg:py-28">
        {/* Copy column */}
        <motion.div
          className="lg:col-span-5"
          initial="hidden"
          animate="visible"
          variants={v(containerVariants)}
        >
          <motion.span
            variants={v(fadeUpVariants)}
            className="badge-soft"
            data-testid="hero-badge"
          >
            <Sparkles aria-hidden className="h-3.5 w-3.5" />
            {TRIAL_DAYS}-day free trial · no card required
          </motion.span>

          <h1 className="mt-6 text-[2.5rem] font-semibold leading-[1.05] tracking-tight text-ink sm:text-5xl lg:text-[3.5rem]">
            {preWords.map((word, i) => (
              <motion.span
                key={`pre-${i}`}
                variants={v(wordVariants)}
                className="inline-block whitespace-pre"
              >
                {word}{' '}
              </motion.span>
            ))}
            <motion.span
              variants={v(wordVariants)}
              className="inline-block bg-clip-text text-transparent"
              style={{ backgroundImage: gradient.blueToPurple }}
            >
              {HEADLINE_GRADIENT}
            </motion.span>{' '}
            {postWords.map((word, i) => (
              <motion.span
                key={`post-${i}`}
                variants={v(wordVariants)}
                className="inline-block whitespace-pre"
              >
                {word}{' '}
              </motion.span>
            ))}
          </h1>

          <motion.p
            variants={v(fadeUpVariants)}
            className="mt-5 max-w-xl text-base leading-relaxed text-ink-muted sm:text-lg"
          >
            Library, Reader, Statistics, Meta-analysis, Manuscript editor, Peer
            Review — built for clinicians who want one app instead of six tabs,
            with their data on their own laptop.
          </motion.p>

          <motion.div
            variants={v(fadeUpVariants)}
            className="mt-8 flex flex-col items-start gap-3 sm:flex-row sm:items-center"
          >
            <motion.div variants={v(ctaVariants)}>
              <Link className="btn-primary" to="/signup" data-testid="hero-primary-cta">
                Start free trial
                <ArrowRight aria-hidden className="h-4 w-4" />
              </Link>
            </motion.div>
            <motion.a
              variants={v(ctaVariants)}
              className="btn-secondary"
              href="#features"
              data-testid="hero-secondary-cta"
            >
              See features
            </motion.a>
          </motion.div>

          <motion.p
            variants={v(fadeUpVariants)}
            className="mt-4 text-xs text-ink-soft"
          >
            Already have an account?{' '}
            <Link to="/login" className="link-soft">
              Sign in
            </Link>
            .
          </motion.p>
        </motion.div>

        {/* Screenshot column */}
        <motion.div
          className="lg:col-span-7"
          initial="hidden"
          animate="visible"
          variants={v(screenshotVariants)}
        >
          <div className="relative">
            <div
              aria-hidden
              className="absolute -inset-8 -z-10 rounded-[2rem] opacity-70 blur-3xl"
              style={{
                background:
                  'linear-gradient(120deg, rgba(37,99,235,0.18) 0%, rgba(124,58,237,0.16) 60%, rgba(255,255,255,0) 100%)',
              }}
            />
            <ScreenshotFrame
              src="/screenshots/manuscript@2x.png"
              alt="Research Assistant manuscript editor with citations, tables and figures"
              urlLabel="manuscripts.local · ACL reconstruction review"
              priority
              data-testid="hero-screenshot"
              className="aspect-[1440/900]"
            />
          </div>
        </motion.div>
      </div>
    </section>
  )
}
