import { BubbleMenu, type Editor } from '@tiptap/react'
import { DOMSerializer } from '@tiptap/pm/model'
import { useMutation } from '@tanstack/react-query'
import { Pencil, Scissors, Sparkles, Wand2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { aiSafeTextToHtml, htmlToAiSafeText } from '@/lib/citationSerialize'
import { type WritingAction, writingApi } from '@/lib/api'

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

export function BubbleAIMenu({
  editor,
  validArticleIds,
}: {
  editor: Editor
  validArticleIds: Set<string>
}) {
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

  function handleAccept(text: string) {
    const { from, to } = editor.state.selection
    editor.chain().focus().deleteRange({ from, to }).insertContent(text).run()
    setSuggestion(null)
    toast.success('Replaced')
  }

  return (
    <BubbleMenu
      editor={editor}
      tippyOptions={{ duration: 120, placement: 'top' }}
      shouldShow={({ from, to }) => to > from}
    >
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-1 rounded-md border border-border bg-white px-1.5 py-1 shadow-md">
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
          <div className="w-[460px]">
            <AISuggestionBlock
              text={suggestion}
              pending={assist.isPending}
              onAccept={handleAccept}
              onReject={() => setSuggestion(null)}
            />
          </div>
        )}
      </div>
    </BubbleMenu>
  )
}
