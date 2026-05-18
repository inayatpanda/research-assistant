import { Copy, MapPin } from 'lucide-react'
import { useState } from 'react'

import { Button } from '@/components/ui/button'
import type { BibliographyEntry } from '@/lib/api'

export function BibliographyRow({
  entry,
  onCopy,
  onLocate,
}: {
  entry: BibliographyEntry
  onCopy: (entry: BibliographyEntry) => void
  onLocate: (entry: BibliographyEntry) => void
}) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    onCopy(entry)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1200)
  }

  return (
    <li className="group flex gap-2 py-2 border-b border-border last:border-b-0">
      <span className="font-mono text-[11px] tabular-nums text-muted-foreground w-7 shrink-0 pt-[2px]">
        [{entry.number}]
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-[12.5px] leading-[18px] text-foreground break-words">
          {entry.formatted_entry}
        </p>
        {entry.first_section && (
          <button
            type="button"
            onClick={() => onLocate(entry)}
            className="mt-1 inline-flex items-center gap-1 text-[10.5px] uppercase tracking-wider text-muted-foreground hover:text-foreground transition-colors"
            title={`Jump to first citation in ${entry.first_section}`}
          >
            <MapPin className="h-3 w-3" />
            Locate in {entry.first_section}
          </button>
        )}
      </div>
      <Button
        size="sm"
        variant="ghost"
        onClick={handleCopy}
        className="h-7 w-7 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
        title={copied ? 'Copied' : 'Copy entry'}
        aria-label="Copy reference entry"
      >
        <Copy className="h-3.5 w-3.5" />
      </Button>
    </li>
  )
}
