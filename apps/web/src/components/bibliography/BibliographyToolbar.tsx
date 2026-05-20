import { ClipboardCopy, Download, Loader2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { CitationStyle } from '@/lib/api'

/**
 * Phase 16 (MP16) — extended catalogue.
 *
 * Vancouver-family journal variants are grouped at the bottom of the select
 * so the canonical four stay on top for users who don't need the
 * journal-specific tweaks.
 */
export const STYLE_OPTIONS: Array<{ value: CitationStyle; label: string }> = [
  { value: 'vancouver', label: 'Vancouver' },
  { value: 'apa', label: 'APA 7' },
  { value: 'harvard', label: 'Harvard' },
  { value: 'ieee', label: 'IEEE' },
  { value: 'lancet', label: 'The Lancet' },
  { value: 'nejm', label: 'NEJM' },
  { value: 'jama', label: 'JAMA' },
  { value: 'bjj', label: 'Bone & Joint Journal' },
  { value: 'jbjs_am', label: 'JBJS (American)' },
  { value: 'bjsm', label: 'BJSM' },
]

export function BibliographyToolbar({
  style,
  onStyleChange,
  onCopyAll,
  onExport,
  busyExport,
  disabled,
}: {
  style: CitationStyle
  onStyleChange: (next: CitationStyle) => void
  onCopyAll: () => void
  onExport: (kind: 'docx' | 'pdf' | 'bibtex' | 'ris' | 'csl-json') => void
  busyExport: 'docx' | 'pdf' | null
  disabled?: boolean
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Select value={style} onValueChange={(v) => onStyleChange(v as CitationStyle)}>
          <SelectTrigger className="h-8 text-[12px] flex-1" aria-label="Citation style">
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
      <div className="flex items-center gap-1.5">
        <Button
          size="sm"
          variant="outline"
          onClick={onCopyAll}
          disabled={disabled}
          className="h-7 text-[11px] flex-1"
        >
          <ClipboardCopy className="h-3 w-3 mr-1" />
          Copy all
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              size="sm"
              variant="outline"
              disabled={disabled}
              className="h-7 text-[11px] flex-1"
            >
              {busyExport ? (
                <Loader2 className="h-3 w-3 mr-1 animate-spin" />
              ) : (
                <Download className="h-3 w-3 mr-1" />
              )}
              Export…
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-44">
            <DropdownMenuLabel className="text-[11px]">Manuscript</DropdownMenuLabel>
            <DropdownMenuItem
              onSelect={() => onExport('docx')}
              disabled={busyExport != null}
              className="text-[12px]"
            >
              {busyExport === 'docx' ? 'Generating DOCX…' : 'DOCX'}
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={() => onExport('pdf')}
              disabled={busyExport != null}
              className="text-[12px]"
            >
              {busyExport === 'pdf' ? 'Generating PDF…' : 'PDF'}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuLabel className="text-[11px]">References</DropdownMenuLabel>
            <DropdownMenuItem onSelect={() => onExport('bibtex')} className="text-[12px]">
              BibTeX (.bib)
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => onExport('ris')} className="text-[12px]">
              RIS (.ris)
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={() => onExport('csl-json')} className="text-[12px]">
              CSL-JSON (.json)
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}
