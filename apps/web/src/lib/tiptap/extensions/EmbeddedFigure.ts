import { Node, mergeAttributes } from '@tiptap/core'

/**
 * `<figure class="prisma-flow|meta-analysis-forest|consort-flow">` atomic
 * block node. Used to preserve push-from-review/meta/consort artefacts on
 * load/save round-trips in the TipTap editor.
 *
 * Without this node the StarterKit schema strips the embedded `<img>` with
 * data: URI (and even the bare `<figure>`/`<figcaption>` wrappers), which
 * caused Bug 3: pushed PRISMA SVG disappears after the user navigates to
 * the section because TipTap silently rewrites the HTML on next autosave.
 *
 * The node is deliberately read-only / atom — researchers re-push from the
 * Review tab to update the diagram rather than editing it inline.
 */

const KNOWN_CLASSES = new Set([
  'prisma-flow',
  'meta-analysis-forest',
  'consort-flow',
])

export interface EmbeddedFigureAttributes {
  src: string
  alt: string
  caption: string
  className: string
}

export const EmbeddedFigure = Node.create({
  name: 'embeddedFigure',
  group: 'block',
  atom: true,
  selectable: true,
  draggable: false,

  addAttributes() {
    return {
      src: {
        default: '',
        parseHTML: (el: HTMLElement) =>
          el.querySelector('img')?.getAttribute('src') ?? '',
      },
      alt: {
        default: '',
        parseHTML: (el: HTMLElement) =>
          el.querySelector('img')?.getAttribute('alt') ?? '',
      },
      caption: {
        default: '',
        parseHTML: (el: HTMLElement) =>
          el.querySelector('figcaption')?.innerHTML ?? '',
      },
      className: {
        default: 'prisma-flow',
        parseHTML: (el: HTMLElement) => {
          const cls = el.getAttribute('class') ?? ''
          for (const k of KNOWN_CLASSES) {
            if (cls.split(/\s+/).includes(k)) return k
          }
          return ''
        },
      },
    }
  },

  parseHTML() {
    return [
      {
        tag: 'figure',
        getAttrs: (node) => {
          if (!(node instanceof HTMLElement)) return false
          const cls = node.getAttribute('class') ?? ''
          if (!cls) return false
          for (const k of KNOWN_CLASSES) {
            if (cls.split(/\s+/).includes(k)) {
              return null  // matches; use parseHTML attribute extractors
            }
          }
          return false
        },
      },
    ]
  },

  renderHTML({ node }) {
    const { src, alt, caption, className } = node.attrs as EmbeddedFigureAttributes
    const figureAttrs = mergeAttributes(
      {},
      className ? { class: className } : {},
    )
    return [
      'figure',
      figureAttrs,
      ['img', { src, alt }],
      ['figcaption', {}, caption],
    ]
  },
})
