import { Mark, mergeAttributes } from '@tiptap/core'

/**
 * Inline mark binding a TipTap range to a `commentId`.
 *
 * Anchors are stored server-side as ProseMirror integer positions, but
 * once applied the mark itself rides along with the document — so edits
 * around the range keep the highlight visually aligned even when the raw
 * positions go stale.
 *
 * Serialised HTML: `<span data-comment data-comment-id="…">…</span>`.
 *
 * No-op (no command) — the route layer creates the comment server-side
 * first, then the editor wraps the selection with the returned `id`.
 */
export const CommentMark = Mark.create({
  name: 'comment',
  inclusive: false,
  spanning: true,

  addAttributes() {
    return {
      commentId: {
        default: null,
        parseHTML: (el) =>
          (el as HTMLElement).getAttribute('data-comment-id'),
        renderHTML: (attrs) =>
          attrs.commentId ? { 'data-comment-id': attrs.commentId } : {},
      },
    }
  },

  parseHTML() {
    return [{ tag: 'span[data-comment]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(
        { 'data-comment': 'true', class: 'comment-mark' },
        HTMLAttributes,
      ),
      0,
    ]
  },

  addCommands() {
    return {
      setComment:
        (commentId: string) =>
        ({ commands }) => {
          return commands.setMark(this.name, { commentId })
        },
      unsetComment:
        () =>
        ({ commands }) => {
          return commands.unsetMark(this.name)
        },
    } as never
  },
})
