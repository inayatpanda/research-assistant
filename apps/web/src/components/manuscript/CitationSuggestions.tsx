import type { Editor } from '@tiptap/react'
import { useEffect, useRef, useState } from 'react'

import type { Article } from '@/lib/api'

/**
 * Minimal `@`-trigger citation picker.
 * Listens for the user typing `@` at a word boundary in the editor; shows a
 * floating dropdown of project articles filtered by the query string. Click
 * inserts a Citation node and removes the trigger text.
 */
export function CitationSuggestions({
  editor,
  articles,
}: {
  editor: Editor
  articles: Article[]
}) {
  const [state, setState] = useState<{
    open: boolean
    query: string
    triggerFrom: number
    rect: DOMRect | null
  } | null>(null)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function updateFromSelection() {
      const { state: editorState } = editor
      const { $from } = editorState.selection
      // Look backwards for an '@' since the last whitespace
      const blockStart = $from.start()
      const text = editorState.doc.textBetween(blockStart, $from.pos, '\n', '\n')
      const atIdx = text.lastIndexOf('@')
      if (atIdx === -1) {
        setState(null)
        return
      }
      const before = atIdx === 0 ? ' ' : text[atIdx - 1]
      if (!/\s|^/.test(before)) {
        setState(null)
        return
      }
      const query = text.slice(atIdx + 1)
      if (/\s/.test(query)) {
        setState(null)
        return
      }
      const triggerFrom = blockStart + atIdx
      const coords = editor.view.coordsAtPos($from.pos)
      setState({
        open: true,
        query,
        triggerFrom,
        rect: new DOMRect(coords.left, coords.bottom, 0, 0),
      })
    }
    editor.on('selectionUpdate', updateFromSelection)
    editor.on('update', updateFromSelection)
    return () => {
      editor.off('selectionUpdate', updateFromSelection)
      editor.off('update', updateFromSelection)
    }
  }, [editor])

  if (!state?.open || !state.rect) return null

  const q = state.query.toLowerCase()
  const matches = articles
    .filter((a) => {
      if (!q) return true
      const hay = `${a.title} ${a.authors.join(' ')} ${a.year ?? ''}`.toLowerCase()
      return hay.includes(q)
    })
    .slice(0, 6)

  function pick(article: Article) {
    if (!state) return
    const to = editor.state.selection.from
    editor
      .chain()
      .focus()
      .deleteRange({ from: state.triggerFrom, to })
      .insertContent({ type: 'citation', attrs: { articleId: article.id } })
      .insertContent(' ')
      .run()
    setState(null)
  }

  return (
    <div
      ref={listRef}
      style={{
        position: 'fixed',
        left: Math.min(window.innerWidth - 340, state.rect.left),
        top: state.rect.top + 4,
        width: 320,
        zIndex: 100,
      }}
      className="rounded-md border border-border bg-white shadow-pop py-1"
    >
      <div className="px-3 py-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
        Cite an article{q ? ` matching "${q}"` : ''}
      </div>
      {matches.length === 0 && (
        <div className="px-3 py-2 text-[12px] text-muted-foreground italic">No matches</div>
      )}
      {matches.map((a) => (
        <button
          key={a.id}
          onMouseDown={(e) => {
            e.preventDefault()
            pick(a)
          }}
          className="w-full text-left px-3 py-2 hover:bg-muted/60 transition-colors"
        >
          <div className="text-[12px] font-medium line-clamp-1">{a.title}</div>
          <div className="text-[11px] text-muted-foreground line-clamp-1">
            {a.authors.slice(0, 2).join(', ')}
            {a.authors.length > 2 ? ` +${a.authors.length - 2}` : ''}
            {a.year ? ` · ${a.year}` : ''}
          </div>
        </button>
      ))}
    </div>
  )
}
