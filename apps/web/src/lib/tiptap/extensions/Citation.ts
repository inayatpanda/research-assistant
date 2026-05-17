import { Node, mergeAttributes } from '@tiptap/core'
import { ReactNodeViewRenderer } from '@tiptap/react'

import { CitationNodeView } from './CitationNodeView'

/**
 * Inline atomic node carrying a single `articleId` attribute.
 *
 * - Serialised HTML: `<sup data-citation data-article-id="…">[…]</sup>`
 * - Rendered in editor: React NodeView reads the current number from
 *   useCitationNumbers and shows `[N]`.
 *
 * The atom flag makes it behave like a single character — backspace deletes
 * the whole citation, not its inner text.
 */
export const Citation = Node.create({
  name: 'citation',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,
  draggable: false,

  addAttributes() {
    return {
      articleId: {
        default: null,
        parseHTML: (el) => (el as HTMLElement).getAttribute('data-article-id'),
        renderHTML: (attrs) =>
          attrs.articleId ? { 'data-article-id': attrs.articleId } : {},
      },
    }
  },

  parseHTML() {
    return [{ tag: 'sup[data-citation]' }]
  },

  renderHTML({ HTMLAttributes, node }) {
    return [
      'sup',
      mergeAttributes(
        { 'data-citation': 'true', class: 'citation' },
        HTMLAttributes,
      ),
      // Placeholder text in saved HTML — the NodeView overlays the real number.
      `[${node.attrs.articleId ? '…' : '?'}]`,
    ]
  },

  addNodeView() {
    return ReactNodeViewRenderer(CitationNodeView)
  },
})
