import { motion } from 'framer-motion'
import { Pencil, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'

import { Button } from '@/components/ui/button'
import { aiSuggestionEnter } from '@/lib/motion'

type State = 'pending' | 'review' | 'edit' | 'accepted' | 'rejected'

/**
 * Reusable AI-suggestion block with Accept / Edit / Reject controls.
 * Reused in Phase 5 manuscript editor.
 */
export function AISuggestionBlock({
  text,
  pending,
  onAccept,
  onReject,
}: {
  text: string | null
  pending: boolean
  onAccept: (text: string) => void
  onReject: () => void
}) {
  const [state, setState] = useState<State>(pending ? 'pending' : text ? 'review' : 'pending')
  const [editedText, setEditedText] = useState(text ?? '')

  useEffect(() => {
    if (pending) setState('pending')
    else if (text) {
      setState('review')
      setEditedText(text)
    }
  }, [text, pending])

  return (
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
        {state === 'accepted' && (
          <span className="text-[10px] uppercase tracking-wider text-emerald-700 font-medium">
            accepted
          </span>
        )}
      </div>

      {state === 'pending' && (
        <div className="text-[12px] text-muted-foreground italic">Drafting…</div>
      )}

      {state === 'edit' && (
        <textarea
          value={editedText}
          onChange={(e) => setEditedText(e.target.value)}
          rows={4}
          className="w-full text-[13px] leading-[20px] rounded-md border border-ai/30 bg-white p-2 focus:outline-none focus:ring-2 focus:ring-ai/30"
        />
      )}

      {(state === 'review' || state === 'accepted') && (
        <div className="text-[13px] leading-[20px]">{editedText}</div>
      )}

      {state === 'review' && (
        <div className="mt-2 flex flex-wrap gap-2">
          <Button
            size="sm"
            onClick={() => {
              setState('accepted')
              onAccept(editedText)
            }}
            className="h-7 text-[12px] bg-ai hover:bg-ai/90 text-white"
          >
            Accept
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setState('edit')}
            className="h-7 text-[12px]"
          >
            <Pencil className="h-3 w-3 mr-1" />
            Edit
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setState('rejected')
              onReject()
            }}
            className="h-7 text-[12px]"
          >
            Reject
          </Button>
        </div>
      )}

      {state === 'edit' && (
        <div className="mt-2 flex flex-wrap gap-2">
          <Button
            size="sm"
            onClick={() => {
              setState('accepted')
              onAccept(editedText)
            }}
            className="h-7 text-[12px] bg-ai hover:bg-ai/90 text-white"
          >
            Save & Accept
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setEditedText(text ?? '')
              setState('review')
            }}
            className="h-7 text-[12px]"
          >
            Cancel edit
          </Button>
        </div>
      )}
    </motion.div>
  )
}
