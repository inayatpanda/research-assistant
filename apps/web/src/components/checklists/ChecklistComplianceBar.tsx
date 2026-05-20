/**
 * MP20 — Compliance progress bar for a reporting-checklist run.
 *
 * Renders a horizontal bar with the pass / fail / unclear / na slices and
 * a numeric label of the compliance percentage. Colours match the rest of
 * the checklist UI (green / red / amber / grey).
 */
export type ChecklistComplianceBarProps = {
  pct: number
  passCount: number
  failCount: number
  unclearCount: number
  naCount: number
  totalCount: number
  className?: string
}

export function ChecklistComplianceBar({
  pct,
  passCount,
  failCount,
  unclearCount,
  naCount,
  totalCount,
  className,
}: ChecklistComplianceBarProps) {
  const denom = totalCount > 0 ? totalCount : 1
  const segments: { key: string; pct: number; className: string }[] = [
    { key: 'pass', pct: (passCount / denom) * 100, className: 'bg-emerald-500' },
    { key: 'fail', pct: (failCount / denom) * 100, className: 'bg-rose-500' },
    { key: 'unclear', pct: (unclearCount / denom) * 100, className: 'bg-amber-500' },
    { key: 'na', pct: (naCount / denom) * 100, className: 'bg-zinc-400' },
  ]
  const colour =
    pct >= 80 ? 'text-emerald-600'
      : pct >= 50 ? 'text-amber-600'
        : 'text-rose-600'

  return (
    <div className={className} data-testid="checklist-compliance-bar">
      <div className="flex items-center justify-between text-xs mb-1">
        <span className={`font-semibold ${colour}`}>
          {pct.toFixed(1)}% compliance
        </span>
        <span className="text-muted-foreground">
          {passCount} pass · {failCount} fail · {unclearCount} unclear · {naCount} N/A
        </span>
      </div>
      <div
        className="flex h-2 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        {segments.map((s) => (
          <div
            key={s.key}
            className={s.className}
            style={{ width: `${s.pct}%` }}
            data-testid={`compliance-seg-${s.key}`}
          />
        ))}
      </div>
    </div>
  )
}
