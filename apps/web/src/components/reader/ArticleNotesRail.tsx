import { formatDistanceToNow } from 'date-fns'
import { ChevronRight, MessageSquareText, NotebookPen } from 'lucide-react'
import { useState } from 'react'

import { useArticleNote } from '@/hooks/useArticleNote'
import { useHighlights } from '@/hooks/useHighlights'
import type { Highlight } from '@/lib/api'
import { useReader } from '@/lib/readerStore'
import { highlightColors, sectionLabels } from '@/lib/tokens'
import { cn } from '@/lib/utils'

/**
 * Right rail. Layout priority is **highlights first** — they're the user's
 * main artefact in the Reader. General article notes get a collapsible panel
 * at the bottom (expanded by default but height-capped).
 */
export function ArticleNotesRail({
  articleId,
  onOpenHighlight,
}: {
  articleId: string
  /** When set, clicking a highlight row in the rail opens the same popover
   * that clicking the on-page highlight opens. The anchor is the rail-row
   * element's bounding rect. */
  onOpenHighlight?: (h: Highlight, anchorRect: DOMRect) => void
}) {
  const { value, setValue, saving, savedAt } = useArticleNote(articleId)
  const { data: highlights = [] } = useHighlights(articleId)
  const setPage = useReader((s) => s.setCurrentPage)
  const [notesOpen, setNotesOpen] = useState(true)

  return (
    <aside className="flex h-full w-full flex-col border-l border-border bg-white">
      {/* HIGHLIGHTS — gets the bulk of the space */}
      <div className="px-5 py-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="text-[14px] font-semibold tracking-tight">Highlights</div>
          <span className="text-[11px] text-muted-foreground tabular-nums">
            {highlights.length}
          </span>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-3 py-2">
        {highlights.length === 0 && (
          <div className="px-2 py-6 text-[12px] text-muted-foreground italic text-center">
            No highlights yet. Press 1–4 then select text in the PDF.
          </div>
        )}
        <div className="space-y-1">
          {highlights.map((h) => {
            const palette = highlightColors[h.colour]
            const hasNote = (h.user_note ?? '').trim().length > 0
            const hasSummary = (h.ai_summary ?? '').trim().length > 0
            return (
              <button
                key={h.id}
                data-highlight-row={h.id}
                onClick={(e) => {
                  setPage(h.page_number)
                  if (onOpenHighlight) {
                    const rect = (
                      e.currentTarget as HTMLElement
                    ).getBoundingClientRect()
                    onOpenHighlight(h, rect)
                  }
                }}
                className="w-full flex items-start gap-2 text-left p-2 rounded-md hover:bg-muted/60 transition-colors"
              >
                <span
                  className="mt-1 inline-block h-2 w-2 rounded-full shrink-0"
                  style={{ background: palette.solid }}
                />
                <div className="min-w-0 flex-1">
                  <div className="text-[12px] line-clamp-2 leading-[16px]">{h.selected_text}</div>
                  {hasNote && (
                    <div className="mt-1 text-[11px] text-muted-foreground italic line-clamp-2 leading-[14px]">
                      “{h.user_note}”
                    </div>
                  )}
                  <div className="mt-1 flex items-center gap-2 text-[10px] text-muted-foreground">
                    <span>{sectionLabels[h.colour]} · p{h.page_number}</span>
                    {hasNote && (
                      <span title="Has paraphrase" className="inline-flex items-center gap-0.5">
                        <MessageSquareText className="h-2.5 w-2.5" />
                      </span>
                    )}
                    {hasSummary && (
                      <span title="AI summary saved" className="text-ai">
                        AI
                      </span>
                    )}
                  </div>
                </div>
                <ChevronRight className="h-3 w-3 text-muted-foreground mt-1 shrink-0" />
              </button>
            )
          })}
        </div>
      </div>

      {/* ARTICLE NOTES — collapsible, capped height */}
      <div className="border-t border-border">
        <button
          onClick={() => setNotesOpen((o) => !o)}
          className="w-full px-5 py-3 flex items-center justify-between hover:bg-muted/40 transition-colors"
        >
          <div className="flex items-center gap-2 text-[13px] font-medium">
            <NotebookPen className="h-3.5 w-3.5 text-muted-foreground" />
            Article notes
          </div>
          <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
            <span>
              {saving
                ? 'Saving…'
                : savedAt
                  ? `Saved ${formatDistanceToNow(new Date(savedAt))} ago`
                  : 'Autosave on'}
            </span>
            <ChevronRight
              className={cn(
                'h-3 w-3 transition-transform',
                notesOpen && 'rotate-90',
              )}
            />
          </div>
        </button>
        {notesOpen && (
          <div className="px-5 pb-3">
            <textarea
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="General thoughts about this article — anything that isn't tied to a single passage."
              rows={5}
              className="w-full h-[120px] resize-none text-[12px] leading-[18px] rounded-md border border-border bg-white p-2.5 focus:outline-none focus:ring-2 focus:ring-accent/40"
            />
          </div>
        )}
      </div>
    </aside>
  )
}
