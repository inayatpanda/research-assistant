import { Check } from 'lucide-react'

/**
 * Horizontal pill-strip immediately below the hero summarising the
 * unique selling points in three or four words each. Keeps the eye
 * moving down the page after the hero CTA before the longer feature
 * explanations start.
 */
const POINTS = [
  'Built by clinicians, for clinicians',
  'Open source',
  'No telemetry',
  'No subscription',
] as const

export function TrustStrip() {
  return (
    <section
      aria-label="Trust signals"
      className="border-b border-slate-200 bg-white"
      data-testid="trust-strip"
    >
      <div className="container-wide flex flex-wrap items-center justify-center gap-x-8 gap-y-3 py-6 text-xs font-medium text-ink-soft sm:text-sm">
        {POINTS.map((point) => (
          <span key={point} className="inline-flex items-center gap-2">
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-accent-tint text-accent">
              <Check aria-hidden className="h-3 w-3" />
            </span>
            {point}
          </span>
        ))}
      </div>
    </section>
  )
}
