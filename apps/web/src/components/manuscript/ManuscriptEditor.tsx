import CharacterCount from '@tiptap/extension-character-count'
import Placeholder from '@tiptap/extension-placeholder'
import StarterKit from '@tiptap/starter-kit'
import { EditorContent, useEditor } from '@tiptap/react'
import { useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

import { useManuscript } from '@/hooks/useManuscript'
import { articlesApi, type ManuscriptSectionName } from '@/lib/api'
import { useQuery } from '@tanstack/react-query'

import { Citation } from '@/lib/tiptap/extensions/Citation'
import { numberCitationsFromHtml } from '@/lib/tiptap/citationEngine'
import { useCitationNumbers } from '@/lib/tiptap/citationNumbers'

import { BubbleAIMenu } from './BubbleAIMenu'
import { CitationSuggestions } from './CitationSuggestions'

export function ManuscriptEditor({
  projectId,
  section,
  onWordsChange,
}: {
  projectId: string
  section: ManuscriptSectionName
  onWordsChange?: (n: number) => void
}) {
  const { html, setHtml, loading } = useManuscript(projectId, section)
  const setMap = useCitationNumbers((s) => s.setMap)
  const [searchParams, setSearchParams] = useSearchParams()
  const { data: articles = [] } = useQuery({
    queryKey: ['articles', projectId],
    queryFn: () => articlesApi.list(projectId),
  })

  const validIds = useMemo(() => new Set(articles.map((a) => a.id)), [articles])

  const editor = useEditor(
    {
      extensions: [
        StarterKit.configure({ heading: { levels: [2, 3] } }),
        Placeholder.configure({
          placeholder:
            'Start writing this section, type @ to cite an article, or paste from Compile.',
        }),
        CharacterCount.configure({ limit: 200_000 }),
        Citation,
      ],
      content: html,
      onUpdate: ({ editor: ed }) => {
        const next = ed.getHTML()
        setHtml(next)
        const map = numberCitationsFromHtml(next)
        setMap(map)
        if (onWordsChange) onWordsChange(ed.storage.characterCount.words())
      },
      editorProps: {
        attributes: {
          class:
            'prose prose-zinc max-w-none focus:outline-none px-10 py-12 font-serif text-[16px] leading-[28px] min-h-[480px]',
          spellcheck: 'true',
        },
      },
    },
    [projectId, section],
  )

  // When the loaded HTML arrives (or section changes), push into the editor.
  // Depends on `html` because cached query data means `loading` may never flip.
  useEffect(() => {
    if (!editor) return
    if (loading) return
    const current = editor.getHTML()
    if (current === html) return
    editor.commands.setContent(html, { emitUpdate: false })
    setMap(numberCitationsFromHtml(html))
    onWordsChange?.(editor.storage.characterCount.words())
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loading, editor, html])

  // Scroll-to-cite: deep links from the bibliography panel land with
  // ?scrollTo=cite-<articleId>. After the editor is mounted with content,
  // walk the doc, locate the first matching citation node, place the
  // selection there, and scroll it into view. Strip the param after handling
  // so refreshing the page does not re-scroll.
  useEffect(() => {
    if (!editor) return
    if (loading) return
    const scrollTo = searchParams.get('scrollTo')
    if (!scrollTo) return
    const match = /^cite-(.+)$/.exec(scrollTo)
    if (!match) return
    const targetId = match[1]
    let pos: number | null = null
    editor.state.doc.descendants((node, p) => {
      if (pos != null) return false
      if (node.type.name === 'citation' && node.attrs.articleId === targetId) {
        pos = p
        return false
      }
      return true
    })
    if (pos != null) {
      editor.commands.setTextSelection(pos)
      editor.commands.scrollIntoView()
      editor.commands.focus()
    }
    const next = new URLSearchParams(searchParams)
    next.delete('scrollTo')
    setSearchParams(next, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editor, loading, html, searchParams])

  if (!editor) return null

  return (
    <div className="flex-1 min-h-0 overflow-y-auto bg-white">
      <EditorContent editor={editor} />
      <BubbleAIMenu editor={editor} validArticleIds={validIds} />
      <CitationSuggestions editor={editor} articles={articles} />
    </div>
  )
}
