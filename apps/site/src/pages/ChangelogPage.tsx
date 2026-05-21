import { CHANGELOG } from '@/data/changelog'

function formatDate(iso: string): string {
  // Hand-author dates are ISO strings; render as e.g. "21 May 2026".
  const d = new Date(iso + 'T00:00:00Z')
  return d.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })
}

export default function ChangelogPage() {
  return (
    <div className="py-16 sm:py-20">
      <div className="container-narrow">
        <header>
          <span className="badge-soft">Changelog</span>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">Releases</h1>
          <p className="mt-3 text-base text-ink-muted">
            Notable additions, fixes and polish, newest first.
          </p>
        </header>

        <ol className="mt-12 space-y-8" data-testid="changelog-list">
          {CHANGELOG.map((entry, index) => (
            <li
              key={entry.version}
              data-testid="changelog-entry"
              data-order={index}
              className="surface-card"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-lg font-semibold tracking-tight">
                  <span className="text-accent">{entry.version}</span>
                  <span className="ml-3 text-ink-muted">— {entry.headline}</span>
                </h2>
                <time dateTime={entry.date} className="text-xs text-ink-soft">
                  {formatDate(entry.date)}
                </time>
              </div>
              <ul className="mt-4 list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-ink-muted">
                {entry.bullets.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </li>
          ))}
        </ol>

        <p className="mt-12 text-xs text-ink-soft">
          Future versions will be auto-generated from GitHub Releases.
        </p>
      </div>
    </div>
  )
}
