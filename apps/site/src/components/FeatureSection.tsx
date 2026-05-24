import type { ReactNode } from 'react'
import { Check } from 'lucide-react'
import { ScreenshotFrame, PhoneFrame } from './ScreenshotFrame'

/**
 * Alternating image-left / image-right feature block. Used seven
 * times on the home page, once each for: Library, Reader, Manuscript,
 * Statistics + Meta-analysis, Peer Review, Submission, Mobile.
 *
 * The `side` prop drives whether the screenshot sits on the left or
 * the right at lg+; at mobile widths the screenshot always sits below
 * the copy.
 *
 * `screenshots` can be one or two images. Two are used for Statistics
 * (statistics + meta-analysis) and Mobile (library + reader) so a
 * single block tells the full story without bloating the page.
 */
export interface FeatureScreenshot {
  src: string
  alt: string
  urlLabel?: string
  /**
   * If true, render inside the PhoneFrame (mobile chrome) instead of a
   * desktop browser chrome. Used for the Mobile PWA section.
   */
  mobile?: boolean
}

interface FeatureSectionProps {
  id: string
  eyebrow: string
  title: string
  body: ReactNode
  bullets: readonly string[]
  side: 'left' | 'right'
  screenshots: readonly FeatureScreenshot[]
  /** Optional accent colour for the eyebrow tag (defaults to accent). */
  tint?: 'accent' | 'ai' | 'emerald' | 'amber'
}

const TINT_CLASSES: Record<NonNullable<FeatureSectionProps['tint']>, string> = {
  accent: 'bg-accent-tint text-accent',
  ai: 'bg-ai-tint text-ai',
  emerald: 'bg-emerald-50 text-emerald-700',
  amber: 'bg-amber-50 text-amber-700',
}

export function FeatureSection({
  id,
  eyebrow,
  title,
  body,
  bullets,
  side,
  screenshots,
  tint = 'accent',
}: FeatureSectionProps) {
  const copyOrder = side === 'left' ? 'lg:order-2' : 'lg:order-1'
  const visualOrder = side === 'left' ? 'lg:order-1' : 'lg:order-2'

  return (
    <section
      id={id}
      data-testid={`feature-section-${id}`}
      className="border-b border-slate-100 py-20 sm:py-24"
    >
      <div className="container-wide grid items-center gap-10 lg:grid-cols-12 lg:gap-16">
        {/* Copy */}
        <div className={['lg:col-span-5', copyOrder].join(' ')}>
          <span
            className={[
              'inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em]',
              TINT_CLASSES[tint],
            ].join(' ')}
            data-testid="feature-eyebrow"
          >
            {eyebrow}
          </span>
          <h2 className="mt-4 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">
            {title}
          </h2>
          <div className="mt-4 text-base leading-relaxed text-ink-muted">{body}</div>
          <ul className="mt-6 space-y-3" data-testid="feature-bullets">
            {bullets.map((bullet) => (
              <li key={bullet} className="flex items-start gap-3">
                <span
                  className={[
                    'mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full',
                    TINT_CLASSES[tint],
                  ].join(' ')}
                >
                  <Check aria-hidden className="h-3 w-3" />
                </span>
                <span className="text-sm leading-relaxed text-ink">{bullet}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Visual(s) */}
        <div className={['lg:col-span-7', visualOrder].join(' ')}>
          {screenshots.length === 1 ? (
            <FeatureScreenshotSingle s={screenshots[0]} />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2">
              {screenshots.map((s, i) => (
                <FeatureScreenshotSingle key={s.src} s={s} compact={i === 1} />
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function FeatureScreenshotSingle({
  s,
  compact = false,
}: {
  s: FeatureScreenshot
  compact?: boolean
}) {
  if (s.mobile) {
    return (
      <div className={compact ? 'flex justify-center' : 'flex justify-center'}>
        <PhoneFrame src={s.src} alt={s.alt} />
      </div>
    )
  }
  return (
    <ScreenshotFrame
      src={s.src}
      alt={s.alt}
      urlLabel={s.urlLabel}
      frameClassName={compact ? '' : ''}
    />
  )
}
