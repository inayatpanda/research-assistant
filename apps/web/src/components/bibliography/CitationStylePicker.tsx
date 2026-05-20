/**
 * Phase 16 (MP16) — Stand-alone citation-style picker.
 *
 * Renders the same 10-style select used by ``BibliographyToolbar`` but as a
 * stand-alone control so it can be embedded in project settings + the
 * compile panel without dragging the rest of the toolbar in.
 */
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { CitationStyle } from '@/lib/api'

import { STYLE_OPTIONS } from './BibliographyToolbar'

export function CitationStylePicker({
  value,
  onChange,
  label,
  disabled,
}: {
  value: CitationStyle
  onChange: (next: CitationStyle) => void
  label?: string
  disabled?: boolean
}) {
  return (
    <div className="space-y-1.5">
      {label ? (
        <label className="text-[11px] font-medium text-muted-foreground">
          {label}
        </label>
      ) : null}
      <Select
        value={value}
        onValueChange={(v) => onChange(v as CitationStyle)}
        disabled={disabled}
      >
        <SelectTrigger className="h-8 text-[12px]" aria-label="Citation style">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {STYLE_OPTIONS.map((s) => (
            <SelectItem key={s.value} value={s.value} className="text-[12px]">
              {s.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
