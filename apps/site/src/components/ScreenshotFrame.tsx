import type { ImgHTMLAttributes } from 'react'

/**
 * Wraps a screenshot in a faux browser-window chrome (traffic-light
 * dots + URL bar) so app captures embed cleanly into the marketing
 * site without feeling like clip-art.
 *
 * Used everywhere a real `apps/web` screenshot is shown — hero, feature
 * sections, sync page. Mobile screenshots are framed by a different
 * device-shaped wrapper (`PhoneFrame`) so the chrome doesn't look out
 * of place against a 390-px-wide PNG.
 */
interface ScreenshotFrameProps extends ImgHTMLAttributes<HTMLImageElement> {
  src: string
  alt: string
  /**
   * Optional URL bar caption. Defaults to a tailnet-style URL because
   * that's the most common context (the site sells the tailnet sync
   * feature heavily).
   */
  urlLabel?: string
  /** Optional extra classes on the outer frame wrapper. */
  frameClassName?: string
  /**
   * Hint that this image should be eagerly preloaded — defaults to
   * true for the hero, false everywhere else.
   */
  priority?: boolean
}

export function ScreenshotFrame({
  src,
  alt,
  urlLabel = 'research-assistant.local',
  frameClassName = '',
  priority = false,
  className = '',
  ...rest
}: ScreenshotFrameProps) {
  return (
    <div
      className={[
        'overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-2xl shadow-slate-900/10',
        frameClassName,
      ].join(' ')}
    >
      {/* Window chrome */}
      <div className="flex items-center gap-2 border-b border-slate-200/80 bg-slate-50 px-3 py-2">
        <span className="h-3 w-3 rounded-full bg-rose-400/90" aria-hidden />
        <span className="h-3 w-3 rounded-full bg-amber-300/90" aria-hidden />
        <span className="h-3 w-3 rounded-full bg-emerald-400/90" aria-hidden />
        <div
          className="ml-3 flex-1 truncate rounded-md bg-white/80 px-3 py-1 text-[11px] font-mono text-ink-soft shadow-inner"
          aria-hidden
        >
          {urlLabel}
        </div>
      </div>
      <img
        src={src}
        alt={alt}
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
        className={['block w-full', className].join(' ')}
        {...rest}
      />
    </div>
  )
}

/**
 * Mobile phone frame — narrower, taller, and rounded like an iPhone.
 * Used for the mobile-library / mobile-reader / mobile-stats captures.
 */
export function PhoneFrame({
  src,
  alt,
  className = '',
  ...rest
}: ImgHTMLAttributes<HTMLImageElement> & { src: string; alt: string }) {
  return (
    <div
      className={[
        'relative mx-auto w-[260px] overflow-hidden rounded-[40px] border-[10px] border-sidebar bg-sidebar shadow-2xl shadow-slate-900/30',
        className,
      ].join(' ')}
    >
      <div className="absolute left-1/2 top-1.5 z-10 h-1.5 w-20 -translate-x-1/2 rounded-full bg-sidebar/80" />
      <img
        src={src}
        alt={alt}
        loading="lazy"
        decoding="async"
        className="block w-full rounded-[30px]"
        {...rest}
      />
    </div>
  )
}
