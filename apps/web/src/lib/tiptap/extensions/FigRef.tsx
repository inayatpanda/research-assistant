/**
 * Phase 4.5 — FigRef TipTap node.
 *
 * Inline atomic node that references a project figure by id. The visible
 * "Figure N" label is read live from ``useFigureNumbers`` so when the
 * Auto-renumber pass updates the store, every existing FigRef updates
 * in-place without an editor reload.
 *
 * Serialised form:
 *     <span class="figref" data-figure-id="<uuid>">Figure ?</span>
 *
 * On parse, the data-figure-id is preserved. The literal "Figure ?" text
 * inside the <span> is a fallback that's overwritten by the NodeView at
 * render time; it only shows when the document is exported with no
 * accompanying figure-number map (e.g. raw HTML preview).
 */
import { Node, mergeAttributes } from '@tiptap/core'
import {
  NodeViewWrapper,
  ReactNodeViewRenderer,
  type NodeViewProps,
} from '@tiptap/react'

import { useFigureNumbers } from '../figureNumbers'

export interface FigRefAttributes {
  figureId: string
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    figref: {
      insertFigRef: (attrs: FigRefAttributes) => ReturnType
    }
  }
}

export const FigRef = Node.create({
  name: 'figref',
  group: 'inline',
  inline: true,
  atom: true,
  selectable: true,

  addAttributes() {
    return {
      figureId: {
        default: null,
        parseHTML: (el: HTMLElement) => el.getAttribute('data-figure-id'),
        renderHTML: (attrs: { figureId: string | null }) =>
          attrs.figureId ? { 'data-figure-id': attrs.figureId } : {},
      },
    }
  },

  parseHTML() {
    return [{ tag: 'span.figref[data-figure-id]' }]
  },

  renderHTML({ node, HTMLAttributes }) {
    const figureId = (node.attrs as FigRefAttributes).figureId ?? ''
    return [
      'span',
      mergeAttributes(HTMLAttributes, {
        class: 'figref',
        ...(figureId ? { 'data-figure-id': figureId } : {}),
      }),
      'Figure ?',
    ]
  },

  addCommands() {
    return {
      insertFigRef:
        (attrs: FigRefAttributes) =>
        ({ commands }) =>
          commands.insertContent({ type: this.name, attrs }),
    }
  },

  addNodeView() {
    return ReactNodeViewRenderer(FigRefNodeView)
  },
})

function FigRefNodeView({ node }: NodeViewProps) {
  const { figureId } = node.attrs as FigRefAttributes
  // Subscribe to the shared figure-number map. Reading via the selector
  // means the NodeView re-renders ONLY when the specific figure number
  // changes (not on unrelated map updates).
  const num = useFigureNumbers((s) => s.map.get(figureId))
  const label = num != null ? `Figure ${num}` : 'Figure ?'
  return (
    <NodeViewWrapper
      as="span"
      className="figref text-foreground"
      data-figure-id={figureId}
      data-testid="figref"
    >
      {label}
    </NodeViewWrapper>
  )
}
