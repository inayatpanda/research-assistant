import * as PopoverPrimitive from '@radix-ui/react-popover'
import { motion } from 'framer-motion'
import { Sparkles, Trash2, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  useDeleteHighlight,
  useSummariseHighlight,
  useUpdateHighlight,
} from '@/hooks/useHighlights'
import type { Highlight } from '@/lib/api'
import { aiSuggestionEnter } from '@/lib/motion'
import { highlightColors, sectionLabels } from '@/lib/tokens'

/**
 * Inline popover anchored on the clicked highlight's <button> rectangle.
 * Auto-focuses the paraphrase field so the user can type immediately.
 */
export function HighlightNotePopover({
  articleId,
  highlight,
  anchorRect,
  onClose,
}: {
  articleId: string
  highlight: Highlight | null
  /** Pixel rect of the clicked highlight in viewport coordinates. Anchors the popover. */
  anchorRect: DOMRect | null
  onClose: () => void
}) {
  const update = useUpdateHighlight(articleId)
  const del = useDeleteHighlight(articleId)
  const summarise = useSummariseHighlight(articleId)

  // Pre-populate from existing user_note on mount so the textbox shows the
  // saved value the moment the popover opens (#H1: previously the field
  // stayed empty until a second render cycle, leading users to assume their
  // note was lost when they reopened a highlight).
  const [note, setNote] = useState(highlight?.user_note ?? '')
  const [aiSummary, setAiSummary] = useState<string | null>(highlight?.ai_summary ?? null)
  const [aiState, setAiState] = useState<'idle' | 'pending' | 'review' | 'accepted'>(
    highlight?.ai_summary ? 'accepted' : 'idle',
  )
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const noteRef = useRef<HTMLTextAreaElement>(null)
  // Hooks must run on every render — keep the anchor ref above any early return.
  const anchorRef = useRef<HTMLElement | null>(null)

  // Build a virtual anchor for Radix Popover so it floats next to the highlight
  if (anchorRect) {
    anchorRef.current = {
      getBoundingClientRect: () => anchorRect,
      getClientRects: () =>
        ({
          length: 1,
          item: () => anchorRect,
          0: anchorRect,
        }) as unknown as DOMRectList,
    } as unknown as HTMLElement
  } else {
    anchorRef.current = null
  }

  // Reset state + focus paraphrase field when a different highlight opens
  useEffect(() => {
    if (!highlight) return
    setNote(highlight.user_note ?? '')
    setAiSummary(highlight.ai_summary)
    setAiState(highlight.ai_summary ? 'accepted' : 'idle')
    setTimeout(() => noteRef.current?.focus(), 80)
  }, [highlight?.id])  // eslint-disable-line react-hooks/exhaustive-deps

  // Debounced note autosave (600ms)
  useEffect(() => {
    if (!highlight) return
    if (note === (highlight.user_note ?? '')) return
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      update.mutate({ id: highlight.id, patch: { user_note: note } })
    }, 600)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [note, highlight, update])

  if (!highlight) return null

  const palette = highlightColors[highlight.colour]

  function handleSummarise() {
    if (!highlight) return
    setAiState('pending')
    summarise.mutate(highlight.id, {
      onSuccess: (updated) => {
        setAiSummary(updated.ai_summary)
        setAiState('review')
      },
      onError: (e: Error) => {
        toast.error(e.message)
        setAiState('idle')
      },
    })
  }

  function handleAcceptAI() {
    setAiState('accepted')
    toast.success('Accepted')
  }

  function handleRejectAI() {
    if (!highlight) return
    update.mutate(
      { id: highlight.id, patch: { ai_summary: null } },
      {
        onSuccess: () => {
          setAiSummary(null)
          setAiState('idle')
        },
      },
    )
  }

  function handleDelete() {
    if (!highlight) return
    if (!confirm('Delete this highlight?')) return
    del.mutate(highlight.id, { onSuccess: onClose })
  }

  return (
    <PopoverPrimitive.Root
      open={!!highlight}
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
    >
      <PopoverPrimitive.Anchor virtualRef={anchorRef} />
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          side="bottom"
          align="start"
          sideOffset={6}
          collisionPadding={16}
          className="z-50 w-[400px] rounded-lg border border-border bg-white outline-none"
          style={{ boxShadow: '0 12px 32px rgba(15,17,23,0.14)' }}
          onOpenAutoFocus={(e) => e.preventDefault()}  // we focus the textarea ourselves
        >
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
            role="dialog"
            aria-label="Highlight note"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-border">
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="inline-block h-3 w-3 rounded-full shrink-0"
                  style={{ background: palette.solid }}
                  aria-hidden
                />
                <div className="text-[13px] font-medium">{sectionLabels[highlight.colour]}</div>
                <div className="text-[11px] text-muted-foreground">· page {highlight.page_number}</div>
              </div>
              <button
                onClick={onClose}
                aria-label="Close"
                className="h-7 w-7 rounded-md hover:bg-muted inline-flex items-center justify-center text-muted-foreground"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="px-4 py-3 space-y-3 max-h-[480px] overflow-y-auto">
              <div
                className="rounded-md p-3 text-[13px] leading-[20px] border"
                style={{ background: palette.fill, borderColor: palette.ring }}
              >
                &ldquo;{highlight.selected_text}&rdquo;
              </div>

              <div>
                <label className="text-[11px] uppercase tracking-wider text-muted-foreground font-medium">
                  Your paraphrase / note
                </label>
                <textarea
                  ref={noteRef}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="How do you want this to read in your manuscript?"
                  rows={3}
                  className="mt-1 w-full text-[13px] rounded-md border border-border bg-white p-2 focus:outline-none focus:ring-2 focus:ring-accent/40"
                />
                <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
                  <span>{update.isPending ? 'Saving…' : note ? 'Autosaves as you type' : ''}</span>
                  <span>{note.length} chars</span>
                </div>
                {!note && (
                  <div className="mt-1.5 text-[11px] text-muted-foreground leading-[15px]">
                    Tip: your paraphrase appears next to the citation when this highlight is compiled into the manuscript.
                  </div>
                )}
              </div>

              {aiState !== 'idle' && (
                <motion.div
                  variants={aiSuggestionEnter}
                  initial="initial"
                  animate="animate"
                  className="rounded-md border bg-ai-tint border-ai/30 p-3"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wider text-ai font-medium">
                      <Sparkles className="h-3 w-3" />
                      AI Suggested
                    </div>
                    {aiState === 'accepted' && (
                      <span className="text-[10px] uppercase tracking-wider text-emerald-700 font-medium">
                        accepted
                      </span>
                    )}
                  </div>
                  {aiState === 'pending' && (
                    <div className="text-[12px] text-muted-foreground italic">Paraphrasing…</div>
                  )}
                  {(aiState === 'review' || aiState === 'accepted') && aiSummary && (
                    <>
                      <div className="text-[13px] leading-[20px]">{aiSummary}</div>
                      {aiState === 'review' && (
                        <div className="mt-2 flex gap-2">
                          <Button
                            size="sm"
                            onClick={handleAcceptAI}
                            className="h-7 text-[12px] bg-ai hover:bg-ai/90 text-white"
                          >
                            Accept
                          </Button>
                          <Button size="sm" variant="ghost" onClick={handleRejectAI} className="h-7 text-[12px]">
                            Reject
                          </Button>
                        </div>
                      )}
                    </>
                  )}
                </motion.div>
              )}

              <div className="flex items-center justify-between pt-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSummarise}
                  disabled={summarise.isPending}
                  className="h-8 text-[12px] border-ai/30 text-ai hover:bg-ai-tint hover:text-ai"
                >
                  <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                  {summarise.isPending ? 'Paraphrasing…' : 'AI Paraphrase'}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleDelete}
                  className="h-8 text-[12px] text-rose-600 hover:text-rose-700 hover:bg-rose-50"
                >
                  <Trash2 className="h-3.5 w-3.5 mr-1" />
                  Delete
                </Button>
              </div>
            </div>
          </motion.div>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  )
}
