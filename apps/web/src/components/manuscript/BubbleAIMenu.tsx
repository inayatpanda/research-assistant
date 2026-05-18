import { DOMSerializer } from '@tiptap/pm/model'
import { useMutation } from '@tanstack/react-query'
import type { Editor } from '@tiptap/react'
import { motion } from 'framer-motion'
import { Pencil, Scissors, Sparkles, Wand2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { type WritingAction, writingApi } from '@/lib/api'
import {
  aiSafeTextToHtml,
  htmlToAiSafeText,
  sanitizeAiHtml,
} from '@/lib/citationSerialize'

import { AISuggestionBlock } from '../compile/AISuggestionBlock'

const ACTIONS: {
  id: WritingAction
  label: string
  icon: React.ComponentType<{ className?: string }>
}[] = [
  { id: 'improve', label: 'Improve', icon: Wand2 },
  { id: 'shorten', label: 'Shorten', icon: Scissors },
  { id: 'formalise', label: 'Formalise', icon: Pencil },
  { id: 'add_transition', label: 'Add transition', icon: Sparkles },
]

function selectionToHtml(editor: Editor): string {
  const { from, to } = editor.state.selection
  if (to <= from) return ''
  const slice = editor.state.doc.slice(from, to)
  const serializer = DOMSerializer.fromSchema(editor.schema)
  const fragment = serializer.serializeFragment(slice.content)
  const div = document.createElement('div')
  div.appendChild(fragment)
  return div.innerHTML
}

/** Position-tracking bubble menu — appears above the selection when the user
 *  highlights a non-empty range. (Bypasses @tiptap/react's BubbleMenu which
 *  moved to a separate package in TipTap 3.) */
export function BubbleAIMenu({
  editor,
  validArticleIds,
}: {
  editor: Editor
  validArticleIds: Set<string>
}) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null)
  const [suggestion, setSuggestion] = useState<string | null>(null)

  const assist = useMutation({
    mutationFn: async (action: WritingAction): Promise<string> => {
      const html = selectionToHtml(editor)
      if (!html) throw new Error('Select some text first')
      const aiSafe = htmlToAiSafeText(html)
      return writingApi.assist(action, aiSafe)
    },
    onSuccess: (revised) => {
      const html = aiSafeTextToHtml(revised, validArticleIds)
      setSuggestion(html)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  useEffect(() => {
    function update() {
      const { from, to } = editor.state.selection
      if (to <= from) {
        // Selection just collapsed — don't tear down the menu while the user is
        // mid-action (a suggestion is being reviewed or a request is in flight).
        if (suggestion || assist.isPending) return
        setPos(null)
        return
      }
      const startCoords = editor.view.coordsAtPos(from)
      const endCoords = editor.view.coordsAtPos(to)
      const x = (startCoords.left + endCoords.right) / 2
      const y = startCoords.top - 8
      setPos({ x, y })
    }
    editor.on('selectionUpdate', update)
    return () => {
      editor.off('selectionUpdate', update)
    }
  }, [editor, suggestion, assist.isPending])

  function handleAccept(text: string) {
    const { from, to } = editor.state.selection
    const clean = sanitizeAiHtml(text)
    editor.chain().focus().deleteRange({ from, to }).insertContent(clean).run()
    setSuggestion(null)
    toast.success('Replaced')
  }

  if (!pos) return null

  const TOOLBAR_W = 380
  const left = Math.max(8, Math.min(window.innerWidth - TOOLBAR_W - 8, pos.x - TOOLBAR_W / 2))
  const top = Math.max(8, pos.y - 50)

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.12 }}
      className="fixed z-50"
      style={{ left, top, width: TOOLBAR_W }}
      onMouseDown={(e) => e.preventDefault()}
    >
      <div className="rounded-md border border-border bg-white px-1.5 py-1 shadow-md flex items-center gap-1">
        {ACTIONS.map((a) => (
          <Button
            key={a.id}
            size="sm"
            variant="ghost"
            disabled={assist.isPending}
            onClick={() => assist.mutate(a.id)}
            className="h-7 px-2 text-[12px] text-ai hover:bg-ai-tint hover:text-ai"
            title={a.label}
          >
            <a.icon className="h-3.5 w-3.5 mr-1" />
            {a.label}
          </Button>
        ))}
      </div>

      {(assist.isPending || suggestion) && (
        <div className="mt-2">
          <AISuggestionBlock
            text={suggestion}
            pending={assist.isPending}
            onAccept={handleAccept}
            onReject={() => setSuggestion(null)}
          />
        </div>
      )}
    </motion.div>
  )
}
