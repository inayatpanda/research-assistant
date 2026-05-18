import { Node, mergeAttributes } from '@tiptap/core'
import { NodeViewWrapper, ReactNodeViewRenderer, type NodeViewProps } from '@tiptap/react'

export interface FigureAttributes {
  figureId: string
  caption: string
  altText: string
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    figure: {
      insertFigure: (attrs: FigureAttributes) => ReturnType
    }
  }
}

/**
 * `<figure data-figure-id="...">` atomic block node.
 *
 * The NodeView fetches the live `file_url` via the figures API so the user
 * sees the actual image. When the URL hasn't resolved yet (or the figure has
 * been deleted server-side), the wrapper falls back to a labelled
 * placeholder so the manuscript remains readable.
 */
export const Figure = Node.create({
  name: 'figure',
  group: 'block',
  atom: true,
  draggable: true,
  selectable: true,

  addAttributes() {
    return {
      figureId: {
        default: null,
        parseHTML: (el: HTMLElement) => el.getAttribute('data-figure-id'),
        renderHTML: (attrs: { figureId: string | null }) =>
          attrs.figureId ? { 'data-figure-id': attrs.figureId } : {},
      },
      caption: {
        default: '',
        parseHTML: (el: HTMLElement) => el.querySelector('figcaption')?.textContent ?? '',
      },
      altText: {
        default: '',
        parseHTML: (el: HTMLElement) => el.querySelector('img')?.getAttribute('alt') ?? '',
      },
    }
  },

  parseHTML() {
    return [{ tag: 'figure[data-figure-id]' }]
  },

  renderHTML({ node, HTMLAttributes }) {
    // Read the canonical attrs from the node directly — `HTMLAttributes` is
    // post-`addAttributes` rendering output, which we keep empty so each
    // attribute gets exactly one home in the serialised HTML.
    const attrs = node.attrs as FigureAttributes
    const figureId = attrs.figureId ?? ''
    const caption = attrs.caption ?? ''
    const alt = attrs.altText ?? ''
    return [
      'figure',
      mergeAttributes(HTMLAttributes, {
        class: 'rma-figure',
        ...(figureId ? { 'data-figure-id': figureId } : {}),
      }),
      ['img', { src: '', alt }],
      ['figcaption', {}, caption],
    ]
  },

  addCommands() {
    return {
      insertFigure:
        (attrs: FigureAttributes) =>
        ({ commands }) =>
          commands.insertContent({ type: this.name, attrs }),
    }
  },

  addNodeView() {
    return ReactNodeViewRenderer(FigureNodeView)
  },
})

function FigureNodeView({ node }: NodeViewProps) {
  const { figureId, caption, altText } = node.attrs as FigureAttributes
  return (
    <NodeViewWrapper as="figure" className="rma-figure" data-figure-id={figureId}>
      <FigureImage figureId={figureId} alt={altText} />
      <figcaption className="text-sm text-muted-foreground mt-2">{caption}</figcaption>
    </NodeViewWrapper>
  )
}

/**
 * Thin wrapper to look up the signed `file_url` for an existing figure.
 * Implementation is split off so tests can render the Figure node without
 * pulling in react-query.
 */
function FigureImage({ figureId, alt }: { figureId: string; alt: string }) {
  // Importing inside the component sidesteps the test runner trying to
  // resolve react-query when it just wants to verify parseHTML/renderHTML.
  // eslint-disable-next-line @typescript-eslint/no-require-imports, @typescript-eslint/no-var-requires
  const { useFigure } = require('@/hooks/useFigures') as typeof import('@/hooks/useFigures')
  const fig = useFigure(figureId)
  if (fig?.file_url) {
    return <img src={fig.file_url} alt={alt} className="max-w-full h-auto" />
  }
  return (
    <div className="rma-figure-placeholder border border-dashed border-border bg-muted/30 px-4 py-8 text-center text-sm text-muted-foreground">
      Figure {figureId ? figureId.slice(0, 6) : '—'} (loading…)
    </div>
  )
}
