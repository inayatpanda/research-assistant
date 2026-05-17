import { motion } from 'framer-motion'
import { Sparkles, Trash2, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'

import {
  useDeleteHighlight,
  useSummariseHighlight,
  useUpdateHighlight,
} from '@/hooks/useHighlights'
import type { Highlight } from '@/lib/api'
import { aiSuggestionEnter } from '@/lib/motion'
import { highlightColors, sectionLabels } from '@/lib/tokens'
import { cn } from '@/lib/utils'

import { Button } from '@/components/ui/button'

export function HighlightNotePopover({
  articleId,
  highlight,
  onClose,
}: {
  articleId: string
  highlight: Highlight | null
  onClose: () => void
}) {
  const update = useUpdateHighlight(articleId)
  const del = useDeleteHighlight(articleId)
  const summarise = useSummariseHighlight(articleId)

  const [note, setNote] = useState('')
  const [aiSummary, setAiSummary] = useState<string | null>(null)
  const [aiState, setAiState] = useState<'idle' | 'pending' | 'review' | 'accepted'>('idle')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Reset state when a different highlight opens
  useEffect(() => {
    if (!highlight) return
    setNote(highlight.user_note ?? '')
    setAiSummary(highlight.ai_summary)
    setAiState(highlight.ai_summary ? 'accepted' : 'idle')
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
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.18 }}
      className="fixed bottom-6 right-6 z-50 w-[400px] rounded-lg border border-border bg-white shadow-pop"
      style={{ boxShadow: '0 12px 32px rgba(15,17,23,0.14)' }}
      role="dialog"
      aria-label="Highlight note"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <span
            className="inline-block h-3 w-3 rounded-full"
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

      <div className="px-4 py-3 space-y-3 max-h-[520px] overflow-y-auto">
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
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="How do you want this to read in your manuscript?"
            rows={3}
            className="mt-1 w-full text-[13px] rounded-md border border-border bg-white p-2 focus:outline-none focus:ring-2 focus:ring-accent/40"
          />
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
              <div className="text-[12px] text-muted-foreground italic">Summarising…</div>
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
            className={cn('h-8 text-[12px]', 'border-ai/30 text-ai hover:bg-ai-tint hover:text-ai')}
          >
            <Sparkles className="h-3.5 w-3.5 mr-1.5" />
            {summarise.isPending ? 'Summarising…' : 'AI Summarise'}
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
  )
}
