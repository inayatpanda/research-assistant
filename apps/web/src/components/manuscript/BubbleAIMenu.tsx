import { DOMSerializer } from '@tiptap/pm/model'
import { useMutation } from '@tanstack/react-query'
import type { Editor } from '@tiptap/react'
import { motion } from 'framer-motion'
import {
  MessageSquarePlus,
  Pencil,
  Scissors,
  Sparkles,
  Wand2,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { useCreateComment } from '@/hooks/useComments'
import {
  type CommentSection,
  type WritingAction,
  writingApi,
} from '@/lib/api'
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
  projectId,
  section,
}: {
  editor: Editor
  validArticleIds: Set<string>
  /** When provided, enables the "Comment" button next to the AI actions. */
  projectId?: string
  /** Manuscript section the editor is bound to — required for commenting. */
  section?: CommentSection
}) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null)
  const [suggestion, setSuggestion] = useState<string | null>(null)
  const [commentMode, setCommentMode] = useState(false)
  const [commentBody, setCommentBody] = useState('')
  const create = useCreateComment(projectId ?? '')

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
        if (suggestion || assist.isPending || commentMode) return
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
  }, [editor, suggestion, assist.isPending, commentMode])

  async function handleCommitComment() {
    if (!projectId || !section) {
      toast.error('Comment binding missing')
      return
    }
    const body = commentBody.trim()
    if (!body) {
      toast.error('Write a comment first')
      return
    }
    const { from, to } = editor.state.selection
    if (to <= from) {
      toast.error('Select some text first')
      return
    }
    try {
      await create.mutateAsync({
        section_name: section,
        anchor_start: from,
        anchor_end: to,
        body,
      })
      toast.success('Comment added')
      setCommentBody('')
      setCommentMode(false)
      setPos(null)
    } catch {
      toast.error('Could not save comment')
    }
  }

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
        {projectId && section ? (
          <Button
            size="sm"
            variant="ghost"
            disabled={assist.isPending}
            onClick={() => setCommentMode((m) => !m)}
            className="h-7 px-2 text-[12px]"
            title="Comment"
            data-testid="bubble-comment-toggle"
          >
            <MessageSquarePlus className="h-3.5 w-3.5 mr-1" />
            Comment
          </Button>
        ) : null}
      </div>

      {commentMode && projectId && section ? (
        <div
          className="mt-2 rounded-md border border-border bg-white p-2 shadow-md space-y-2"
          data-testid="bubble-comment-form"
        >
          <textarea
            value={commentBody}
            onChange={(e) => setCommentBody(e.target.value)}
            placeholder="Add a comment…"
            rows={3}
            className="w-full text-[12px] rounded border border-border p-1.5 outline-none focus:ring-1 focus:ring-accent"
            data-testid="bubble-comment-body"
          />
          <div className="flex justify-end gap-1">
            <Button
              size="sm"
              variant="ghost"
              className="h-6 px-2 text-[12px]"
              onClick={() => {
                setCommentMode(false)
                setCommentBody('')
              }}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              className="h-6 px-2 text-[12px]"
              onClick={handleCommitComment}
              disabled={create.isPending}
              data-testid="bubble-comment-submit"
            >
              Save
            </Button>
          </div>
        </div>
      ) : null}

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
