import { Node, mergeAttributes } from '@tiptap/core'

/**
 * Inline atomic node carrying a single `articleId` attribute.
 *
 * Rendered as `<sup data-citation data-article-id="…">[N]</sup>` where N comes
 * from `citationEngine`. The renderer in the editor (citationNumbersDecoration)
 * reads the engine's map and overlays the number.
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
      // Placeholder text — the editor overlays the actual number via a node view.
      `[${node.attrs.articleId ? '…' : '?'}]`,
    ]
  },
})
