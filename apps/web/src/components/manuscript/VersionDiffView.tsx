/**
 * Phase 11 — Side-by-side rendering of a snapshot diff.
 *
 * Reads `SnapshotDiffResponse` (one record per section, each a list of
 * `{type, line}`) and renders each section's diff inline with
 * `<ins>` / `<del>` highlighting. No external dep — the difflib
 * output ships from the backend pre-classified.
 */
import { ScrollArea } from '@/components/ui/scroll-area'
import type { SnapshotDiffResponse } from '@/lib/api'

type Props = {
  diff: SnapshotDiffResponse | undefined
  loading?: boolean
}

export function VersionDiffView({ diff, loading }: Props) {
  if (loading) {
    return (
      <div className="p-4 text-sm text-muted-foreground">Computing diff…</div>
    )
  }
  if (!diff) {
    return (
      <div className="p-4 text-sm text-muted-foreground">
        No diff available.
      </div>
    )
  }
  const sectionNames = Object.keys(diff.sections)
  if (sectionNames.length === 0) {
    return (
      <div
        className="p-4 text-sm text-muted-foreground"
        data-testid="diff-empty"
      >
        No changes between these snapshots.
      </div>
    )
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-3 space-y-4" data-testid="diff-view">
        {sectionNames.map((name) => {
          const lines = diff.sections[name]
          return (
            <section key={name}>
              <h4 className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-1">
                {name}
              </h4>
              <pre className="text-[12px] font-mono whitespace-pre-wrap break-words rounded border border-border bg-zinc-50 p-2">
                {lines.map((d, idx) => {
                  if (d.type === '+') {
                    return (
                      <ins
                        key={idx}
                        className="block bg-emerald-50 text-emerald-900 no-underline"
                        data-diff-type="add"
                      >
                        + {d.line}
                      </ins>
                    )
                  }
                  if (d.type === '-') {
                    return (
                      <del
                        key={idx}
                        className="block bg-rose-50 text-rose-900 no-underline"
                        data-diff-type="del"
                      >
                        - {d.line}
                      </del>
                    )
                  }
                  return (
                    <span
                      key={idx}
                      className="block text-zinc-600"
                      data-diff-type="eq"
                    >
                      {'  '}
                      {d.line}
                    </span>
                  )
                })}
              </pre>
            </section>
          )
        })}
      </div>
    </ScrollArea>
  )
}
