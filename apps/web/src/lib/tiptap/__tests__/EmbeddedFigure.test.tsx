/**
 * EmbeddedFigure round-trip tests.
 *
 * Bug 3 regression: pushed PRISMA / meta-analysis-forest / consort-flow
 * figures must survive a TipTap load → save round-trip without losing the
 * embedded `<img>` (the user complaint was that only the figcaption
 * survived after re-rendering).
 */
import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { describe, expect, it } from 'vitest'

import { EmbeddedFigure } from '../extensions/EmbeddedFigure'

function makeEditor(content: string): Editor {
  return new Editor({
    extensions: [StarterKit, EmbeddedFigure],
    content,
  })
}

describe('EmbeddedFigure TipTap extension', () => {
  it('preserves PRISMA <img> through parseHTML/renderHTML round-trip', () => {
    const html =
      '<figure class="prisma-flow">' +
      '<img src="data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=" alt="PRISMA 2020 flow diagram"/>' +
      '<figcaption>PRISMA 2020 flow diagram.</figcaption>' +
      '</figure>'
    const ed = makeEditor(html)
    const out = ed.getHTML()
    expect(out).toContain('data:image/svg+xml;base64,')
    expect(out).toContain('class="prisma-flow"')
    expect(out).toContain('PRISMA 2020 flow diagram.')
    ed.destroy()
  })

  it('preserves meta-analysis-forest <img> through round-trip', () => {
    const html =
      '<figure class="meta-analysis-forest">' +
      '<img src="data:image/png;base64,iVBORw0KGgo=" alt="Forest plot"/>' +
      '<figcaption>Forest plot caption.</figcaption>' +
      '</figure>'
    const ed = makeEditor(html)
    const out = ed.getHTML()
    expect(out).toContain('data:image/png;base64,')
    expect(out).toContain('class="meta-analysis-forest"')
    ed.destroy()
  })

  it('preserves consort-flow class on round-trip', () => {
    const html =
      '<figure class="consort-flow">' +
      '<img src="data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=" alt="CONSORT"/>' +
      '<figcaption>CONSORT 2010 flow diagram.</figcaption>' +
      '</figure>'
    const ed = makeEditor(html)
    const out = ed.getHTML()
    expect(out).toContain('class="consort-flow"')
    expect(out).toContain('data:image/svg+xml;base64,')
    ed.destroy()
  })

  it('does not absorb generic figures (those go through default schema)', () => {
    // A bare <figure> without a known class should not be claimed by
    // EmbeddedFigure; ProseMirror will drop the wrapper but neither will
    // EmbeddedFigure swallow it.
    const html = '<figure><img src="x" alt="y"/></figure>'
    const ed = makeEditor(html)
    let matched = false
    ed.state.doc.descendants((node) => {
      if (node.type.name === 'embeddedFigure') matched = true
      return true
    })
    expect(matched).toBe(false)
    ed.destroy()
  })

  it('EmbeddedFigure is an atom node', () => {
    const ed = makeEditor('')
    expect(ed.schema.nodes.embeddedFigure.isAtom).toBe(true)
    ed.destroy()
  })
})
