/**
 * Phase 4.5 — FigRef extension parse/render-cycle tests.
 *
 * Mirrors Figure.test.tsx: we exercise the Node's parseHTML / renderHTML /
 * commands by booting a bare tiptap Editor (no React tree) so the test
 * stays fast and independent of the FiguresPanel.
 */
import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { describe, expect, it } from 'vitest'

import { FigRef } from '../extensions/FigRef'

function makeEditor(content = ''): Editor {
  return new Editor({ extensions: [StarterKit, FigRef], content })
}

describe('FigRef TipTap extension', () => {
  it('parses span.figref[data-figure-id] back into an inline atom', () => {
    const ed = makeEditor(
      '<p>See <span class="figref" data-figure-id="fig-1">Figure ?</span> below.</p>',
    )
    let foundId: string | null = null
    ed.state.doc.descendants((node) => {
      if (node.type.name === 'figref') {
        foundId = (node.attrs as { figureId: string }).figureId
      }
      return true
    })
    expect(foundId).toBe('fig-1')
    ed.destroy()
  })

  it('renderHTML emits data-figure-id and the placeholder text', () => {
    const ed = makeEditor('')
    ed.commands.insertFigRef({ figureId: 'fig-9' })
    const html = ed.getHTML()
    expect(html).toMatch(/data-figure-id="fig-9"/)
    expect(html).toMatch(/class="figref"/)
    ed.destroy()
  })

  it('is an inline atom (matches the schema contract)', () => {
    const ed = makeEditor('')
    const type = ed.schema.nodes.figref
    expect(type.isAtom).toBe(true)
    expect(type.isInline).toBe(true)
    ed.destroy()
  })
})
