/**
 * Phase 16 (MP16) — Inline citation rendering mode selector.
 *
 * Three modes, mirrors the backend ``InlineCitationMode`` literal:
 *   * ``bracket_numeric``       → ``[1]``
 *   * ``superscript_numeric``   → ``¹``
 *   * ``author_year_parens``    → ``(Smith 2024)``
 *
 * The TipTap CitationNodeView reads this off project state via
 * ``useInlineCitationMode()`` so the rich editor stays in sync without
 * needing to plumb props through every page.
 */
import type { InlineCitationMode } from '@/lib/api'

const MODES: Array<{
  value: InlineCitationMode
  label: string
  example: string
}> = [
  { value: 'bracket_numeric', label: 'Brackets', example: '[1]' },
  { value: 'superscript_numeric', label: 'Superscript', example: '¹' },
  { value: 'author_year_parens', label: 'Author–year', example: '(Smith 2024)' },
]

export function InlineCitationModeSelector({
  value,
  onChange,
  disabled,
}: {
  value: InlineCitationMode
  onChange: (next: InlineCitationMode) => void
  disabled?: boolean
}) {
  return (
    <div
      role="radiogroup"
      aria-label="Inline citation mode"
      className="flex flex-col gap-1.5"
    >
      {MODES.map((m) => {
        const selected = value === m.value
        return (
          <label
            key={m.value}
            className={`flex items-center gap-2 text-[12px] cursor-pointer rounded-md border px-2.5 py-1.5 transition-colors ${
              selected
                ? 'border-primary bg-primary/5'
                : 'border-border hover:bg-muted/40'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <input
              type="radio"
              name="inline-citation-mode"
              value={m.value}
              checked={selected}
              onChange={() => onChange(m.value)}
              disabled={disabled}
              className="accent-primary"
              aria-label={m.label}
            />
            <span className="font-medium">{m.label}</span>
            <span className="ml-auto text-muted-foreground font-mono">
              {m.example}
            </span>
          </label>
        )
      })}
    </div>
  )
}
