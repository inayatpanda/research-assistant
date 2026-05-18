/**
 * Render-cycle smoke tests for the Figure node. We exercise parseHTML +
 * renderHTML via a fresh Tiptap editor — this confirms the attribute mapping
 * is correct without booting React.
 */
import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { describe, expect, it } from 'vitest'

import { Figure } from '../extensions/Figure'

function makeEditor(content: string): Editor {
  return new Editor({
    extensions: [StarterKit, Figure],
    content,
  })
}

describe('Figure TipTap extension', () => {
  it('parses existing figure HTML and reads attributes', () => {
    const html =
      '<figure data-figure-id="abc123"><img src="" alt="my alt"/><figcaption>Cap</figcaption></figure>'
    const ed = makeEditor(html)
    let foundId: string | null = null
    let foundCaption: string | null = null
    ed.state.doc.descendants((node) => {
      if (node.type.name === 'figure') {
        foundId = (node.attrs as { figureId: string }).figureId
        foundCaption = (node.attrs as { caption: string }).caption
      }
      return true
    })
    expect(foundId).toBe('abc123')
    expect(foundCaption).toBe('Cap')
    ed.destroy()
  })

  it('renderHTML emits the data-figure-id attribute', () => {
    const ed = makeEditor('')
    ed.commands.insertContent({
      type: 'figure',
      attrs: { figureId: 'xyz', caption: 'Foo', altText: 'alt' },
    })
    const out = ed.getHTML()
    expect(out).toMatch(/data-figure-id="xyz"/)
    expect(out).toMatch(/Foo/)
    ed.destroy()
  })

  it('Figure node is an atom (not editable inline)', () => {
    const ed = makeEditor('')
    const schema = ed.schema
    const figureType = schema.nodes.figure
    expect(figureType.isAtom).toBe(true)
    ed.destroy()
  })
})
