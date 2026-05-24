import { Link } from 'react-router-dom'
import { ArrowRight, Sparkles } from 'lucide-react'
import { ScreenshotFrame } from './ScreenshotFrame'
import { dotPattern, gradient } from '@/lib/brandTokens'
import { TRIAL_DAYS } from '@/lib/licenseApi'

/**
 * Marketing hero — top of the home page.
 *
 * Pairs a strong headline with a real manuscript-editor screenshot in
 * a browser-chrome frame. The headline mixes a flat sentence opener
 * with a blue→purple gradient highlight so it scans well in screenshots
 * shared on social cards but never feels like a generic AI gradient.
 *
 * Layout:
 *   - On lg+ the hero is two columns: copy on the left, screenshot
 *     on the right.
 *   - Below lg it stacks vertically. The screenshot is intentionally
 *     not hidden on mobile because the product is mostly visual; we
 *     just let it scroll.
 */
export function Hero() {
  return (
    <section className="relative isolate overflow-hidden border-b border-slate-200 bg-white">
      {/* Soft radial wash + dotted grid sit underneath everything. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{ background: gradient.heroSky }}
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
        <div className="lg:col-span-5">
          <span className="badge-soft" data-testid="hero-badge">
            <Sparkles aria-hidden className="h-3.5 w-3.5" />
            {TRIAL_DAYS}-day free trial · no card required
          </span>
          <h1 className="mt-6 text-[2.5rem] font-semibold leading-[1.05] tracking-tight text-ink sm:text-5xl lg:text-[3.5rem]">
            The local-first{' '}
            <span
              className="bg-clip-text text-transparent"
              style={{ backgroundImage: gradient.blueToPurple }}
            >
              manuscript tool
            </span>{' '}
            for clinical research.
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-ink-muted sm:text-lg">
            Library, Reader, Statistics, Meta-analysis, Manuscript editor, Peer
            Review — built for clinicians who want one app instead of six tabs,
            with their data on their own laptop.
          </p>
          <div className="mt-8 flex flex-col items-start gap-3 sm:flex-row sm:items-center">
            <Link className="btn-primary" to="/signup" data-testid="hero-primary-cta">
              Start free trial
              <ArrowRight aria-hidden className="h-4 w-4" />
            </Link>
            <a
              className="btn-secondary"
              href="#features"
              data-testid="hero-secondary-cta"
            >
              See features
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

        {/* Screenshot column. We bias the screenshot off-axis with a tiny
            rotation so it doesn't read as a stock dashboard pic. */}
        <div className="lg:col-span-7">
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
        </div>
      </div>
    </section>
  )
}
