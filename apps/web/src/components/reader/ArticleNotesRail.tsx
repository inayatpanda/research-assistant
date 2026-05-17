import { formatDistanceToNow } from 'date-fns'
import { ChevronRight, NotebookPen } from 'lucide-react'

import { useHighlights } from '@/hooks/useHighlights'
import { useArticleNote } from '@/hooks/useArticleNote'
import { useReader } from '@/lib/readerStore'
import { highlightColors, sectionLabels } from '@/lib/tokens'

export function ArticleNotesRail({ articleId }: { articleId: string }) {
  const { value, setValue, saving, savedAt, loading } = useArticleNote(articleId)
  const { data: highlights = [] } = useHighlights(articleId)
  const setPage = useReader((s) => s.setCurrentPage)

  return (
    <aside className="hidden lg:flex shrink-0 w-[320px] flex-col border-l border-border bg-white">
      <div className="px-5 py-4 border-b border-border">
        <div className="flex items-center gap-2 text-[14px] font-semibold tracking-tight">
          <NotebookPen className="h-4 w-4 text-muted-foreground" />
          Article notes
        </div>
        <div className="mt-0.5 text-[11px] text-muted-foreground">
          {loading
            ? 'Loading…'
            : saving
              ? 'Saving…'
              : savedAt
                ? `Saved ${formatDistanceToNow(new Date(savedAt))} ago`
                : 'Autosave on'}
        </div>
      </div>

      <div className="px-5 py-3 flex-1 min-h-0 flex flex-col">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="General thoughts about this article — anything that isn't tied to a single passage."
          className="flex-1 min-h-[200px] resize-none text-[13px] leading-[20px] rounded-md border border-border bg-white p-3 focus:outline-none focus:ring-2 focus:ring-accent/40"
        />
      </div>

      <div className="px-5 py-3 border-t border-border">
        <div className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium mb-2">
          Highlights ({highlights.length})
        </div>
        <div className="space-y-1 max-h-[280px] overflow-y-auto">
          {highlights.length === 0 && (
            <div className="text-[12px] text-muted-foreground italic">No highlights yet.</div>
          )}
          {highlights.map((h) => {
            const palette = highlightColors[h.colour]
            return (
              <button
                key={h.id}
                onClick={() => setPage(h.page_number)}
                className="w-full flex items-start gap-2 text-left p-2 rounded-md hover:bg-muted/60 transition-colors"
              >
                <span
                  className="mt-1 inline-block h-2 w-2 rounded-full shrink-0"
                  style={{ background: palette.solid }}
                />
                <div className="min-w-0 flex-1">
                  <div className="text-[12px] truncate">{h.selected_text}</div>
                  <div className="text-[10px] text-muted-foreground">
                    {sectionLabels[h.colour]} · p{h.page_number}
                  </div>
                </div>
                <ChevronRight className="h-3 w-3 text-muted-foreground mt-1" />
              </button>
            )
          })}
        </div>
      </div>
    </aside>
  )
}
