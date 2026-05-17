import { describe, expect, it } from 'vitest'

import {
  numberCitationsAcross,
  numberCitationsFromDoc,
  numberCitationsFromHtml,
} from '../tiptap/citationEngine'

describe('numberCitationsFromDoc', () => {
  it('assigns 1-based numbers in order of first appearance', () => {
    const doc = {
      type: 'doc',
      content: [
        {
          type: 'paragraph',
          content: [
            { type: 'text', text: 'Anterior was faster ' },
            { type: 'citation', attrs: { articleId: 'art-A' } },
            { type: 'text', text: '. Same group reported ' },
            { type: 'citation', attrs: { articleId: 'art-B' } },
            { type: 'text', text: '. Earlier ref ' },
            { type: 'citation', attrs: { articleId: 'art-A' } },
            { type: 'text', text: ' again.' },
          ],
        },
      ],
    }
    const map = numberCitationsFromDoc(doc)
    expect(map.get('art-A')).toBe(1)
    expect(map.get('art-B')).toBe(2)
    expect(map.size).toBe(2)
  })

  it('returns empty map for doc with no citations', () => {
    const doc = { type: 'doc', content: [{ type: 'paragraph', content: [] }] }
    expect(numberCitationsFromDoc(doc).size).toBe(0)
  })
})

describe('numberCitationsFromHtml', () => {
  it('parses sup[data-citation] in HTML', () => {
    const html =
      '<p>X <sup data-citation data-article-id="abc">[1]</sup> Y <sup data-citation data-article-id="xyz">[1]</sup> Z</p>'
    const map = numberCitationsFromHtml(html)
    expect(map.get('abc')).toBe(1)
    expect(map.get('xyz')).toBe(2)
  })

  it('returns empty map for empty input', () => {
    expect(numberCitationsFromHtml('').size).toBe(0)
  })
})

describe('numberCitationsAcross', () => {
  it('numbers continuously across multiple HTML strings', () => {
    const intro = '<p>X <sup data-citation data-article-id="a">[1]</sup></p>'
    const method = '<p>Y <sup data-citation data-article-id="b">[1]</sup></p>'
    const results =
      '<p>Z <sup data-citation data-article-id="a">[1]</sup> <sup data-citation data-article-id="c">[1]</sup></p>'
    const map = numberCitationsAcross([intro, method, results])
    expect(map.get('a')).toBe(1)
    expect(map.get('b')).toBe(2)
    expect(map.get('c')).toBe(3)
    expect(map.size).toBe(3)
  })
})
