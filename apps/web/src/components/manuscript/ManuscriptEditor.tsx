import CharacterCount from '@tiptap/extension-character-count'
import Placeholder from '@tiptap/extension-placeholder'
import StarterKit from '@tiptap/starter-kit'
import { EditorContent, useEditor } from '@tiptap/react'
import { useEffect, useMemo } from 'react'

import { useManuscript } from '@/hooks/useManuscript'
import { articlesApi, type Article, type ManuscriptSectionName } from '@/lib/api'
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

  if (!editor) return null

  return (
    <div className="flex-1 min-h-0 overflow-y-auto bg-white">
      <EditorContent editor={editor} />
      <BubbleAIMenu editor={editor} validArticleIds={validIds} />
      <CitationSuggestions editor={editor} articles={articles} />
    </div>
  )
}
