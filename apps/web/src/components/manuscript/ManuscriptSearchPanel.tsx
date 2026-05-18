/**
 * Cross-section manuscript search panel (BUG #13 + #16).
 *
 * Renders a popover at the top of the manuscript pane with a debounced
 * search input and a hit list grouped by section. Each hit shows a 60-80
 * char preview with the match highlighted. Clicking a hit calls `onJump`
 * with the section + match-within-section index so the parent can switch
 * the active tab and scroll the editor to the right offset.
 *
 * Keyboard: Cmd-G / F3 → next hit, Shift variants → prev hit, Esc → close.
 * Cmd-F itself is registered by `ManuscriptPage` (we don't bind window-level
 * shortcuts inside this component to avoid duplicates when the panel
 * mounts during search).
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { X } from 'lucide-react'

import type { ManuscriptSectionName } from '@/lib/api'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export type SectionHtml = {
  section: ManuscriptSectionName
  html: string
}

export type SearchHit = {
  section: ManuscriptSectionName
  /** Zero-based index of this match within `section`. Used for scroll-to. */
  matchIndex: number
  /** Up to ~80 chars of surrounding plain-text context. */
  preview: string
  /** Character offset (in the plain-text version) of the match start. */
  start: number
  /** Length of the matched substring. */
  length: number
  /** The literal needle (case-preserved as the user typed it). Useful for
   *  the parent's editor-side TextSelection without re-parsing the preview. */
  query: string
}

/** Strip HTML tags and the contents of `<sup data-citation>` markers so the
 *  user does not match `[1]` literals from inline citations. */
function stripHtmlForSearch(html: string): string {
  if (!html) return ''
  // 1) Remove the entire `<sup data-citation ...>...</sup>` token (content + tag).
  let s = html.replace(
    /<sup\s+data-citation\b[^>]*>[\s\S]*?<\/sup>/gi,
    ' ',
  )
  // 2) Strip remaining tags.
  s = s.replace(/<[^>]+>/g, ' ')
  // 3) Decode the most common HTML entities (we don't need a full parser).
  s = s
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
  // 4) Collapse whitespace.
  return s.replace(/\s+/g, ' ').trim()
}

function _buildPreview(text: string, start: number, end: number): string {
  const MAX = 80
  // Aim for the match in the middle of ~80 chars.
  const span = end - start
  const slack = Math.max(0, MAX - span)
  const left = Math.max(0, start - Math.floor(slack / 2))
  const right = Math.min(text.length, left + MAX)
  let preview = text.slice(left, right)
  if (left > 0) preview = '…' + preview.slice(1)
  if (right < text.length) preview = preview.slice(0, -1) + '…'
  return preview
}

function findMatches(
  sections: SectionHtml[],
  rawQuery: string,
): SearchHit[] {
  const query = rawQuery.trim()
  if (!query) return []
  const needle = query.toLowerCase()
  const out: SearchHit[] = []
  for (const { section, html } of sections) {
    const text = stripHtmlForSearch(html)
    if (!text) continue
    const lower = text.toLowerCase()
    let from = 0
    let matchIndex = 0
    while (true) {
      const at = lower.indexOf(needle, from)
      if (at < 0) break
      const end = at + needle.length
      out.push({
        section,
        matchIndex,
        preview: _buildPreview(text, at, end),
        start: at,
        length: needle.length,
        query,
      })
      matchIndex += 1
      from = end
      if (matchIndex > 50) break  // hard cap per section
    }
  }
  return out
}

/** Render the preview with the matched substring wrapped in <mark>. */
function HighlightedPreview({
  preview,
  query,
}: {
  preview: string
  query: string
}) {
  if (!query) return <span>{preview}</span>
  const lower = preview.toLowerCase()
  const lowerNeedle = query.toLowerCase()
  const idx = lower.indexOf(lowerNeedle)
  if (idx < 0) return <span>{preview}</span>
  return (
    <span>
      {preview.slice(0, idx)}
      <mark className="bg-amber-200 rounded px-0.5">
        {preview.slice(idx, idx + lowerNeedle.length)}
      </mark>
      {preview.slice(idx + lowerNeedle.length)}
    </span>
  )
}

export function ManuscriptSearchPanel({
  sections,
  onJump,
  onClose,
}: {
  sections: SectionHtml[]
  onJump: (hit: SearchHit) => void
  onClose: () => void
}) {
  const [query, setQuery] = useState('')
  const [debounced, setDebounced] = useState('')
  const [activeIdx, setActiveIdx] = useState(0)
  const inputRef = useRef<HTMLInputElement | null>(null)

  // Debounce by 150ms.
  useEffect(() => {
    const t = setTimeout(() => setDebounced(query), 150)
    return () => clearTimeout(t)
  }, [query])

  // Focus the input on mount.
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const hits = useMemo(() => findMatches(sections, debounced), [sections, debounced])

  // If hits shrink, keep activeIdx in range.
  useEffect(() => {
    if (activeIdx >= hits.length) setActiveIdx(0)
  }, [hits.length, activeIdx])

  const grouped = useMemo(() => {
    const m = new Map<ManuscriptSectionName, SearchHit[]>()
    for (const h of hits) {
      const arr = m.get(h.section) ?? []
      arr.push(h)
      m.set(h.section, arr)
    }
    return Array.from(m.entries())
  }, [hits])

  function handleKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Escape') {
      e.preventDefault()
      onClose()
      return
    }
    // Cmd-G / Ctrl-G / F3 → next; with Shift → prev.
    const isCmdG = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'g'
    const isF3 = e.key === 'F3'
    if (isCmdG || isF3) {
      e.preventDefault()
      if (!hits.length) return
      const dir = e.shiftKey ? -1 : 1
      const next = (activeIdx + dir + hits.length) % hits.length
      setActiveIdx(next)
      onJump(hits[next])
      return
    }
    if (e.key === 'Enter') {
      e.preventDefault()
      if (!hits.length) return
      const dir = e.shiftKey ? -1 : 1
      const next = (activeIdx + dir + hits.length) % hits.length
      setActiveIdx(next)
      onJump(hits[next])
    }
  }

  return (
    <div
      data-testid="manuscript-search-panel"
      className="absolute right-4 top-2 z-50 w-96 rounded-md border border-border bg-white shadow-md"
    >
      <div className="flex items-center gap-2 border-b border-border p-2">
        <Input
          ref={inputRef}
          placeholder="Search manuscript…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKey}
          className="h-8"
          data-testid="manuscript-search-input"
        />
        <span className="text-[11px] text-muted-foreground whitespace-nowrap tabular-nums">
          {hits.length ? `${activeIdx + 1}/${hits.length}` : '0/0'}
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={onClose}
          aria-label="Close search"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
      <div className="max-h-80 overflow-y-auto p-2 text-sm">
        {debounced && hits.length === 0 && (
          <div className="px-2 py-3 text-xs text-muted-foreground">
            No matches in any section.
          </div>
        )}
        {grouped.map(([section, sectionHits]) => (
          <div key={section} className="mb-2 last:mb-0">
            <div className="px-1 pb-1 text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
              {section} · {sectionHits.length}
            </div>
            <ul className="space-y-0.5">
              {sectionHits.map((hit) => {
                const globalIdx = hits.indexOf(hit)
                const isActive = globalIdx === activeIdx
                return (
                  <li
                    key={`${section}-${hit.matchIndex}`}
                    data-testid="search-hit"
                    role="button"
                    tabIndex={0}
                    onClick={() => {
                      setActiveIdx(globalIdx)
                      onJump(hit)
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        setActiveIdx(globalIdx)
                        onJump(hit)
                      }
                    }}
                    className={
                      'cursor-pointer rounded px-2 py-1 text-[12.5px] leading-snug hover:bg-zinc-100 ' +
                      (isActive ? 'bg-amber-50 ring-1 ring-amber-200' : '')
                    }
                  >
                    <HighlightedPreview preview={hit.preview} query={debounced} />
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </div>
    </div>
  )
}

// Exported for unit tests only.
export const __testing = {
  findMatches,
  stripHtmlForSearch,
}
