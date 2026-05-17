import { describe, expect, it } from 'vitest'

import { aiSafeTextToHtml, htmlToAiSafeText } from '../citationSerialize'

describe('htmlToAiSafeText', () => {
  it('replaces sup data-citation with [CITE_<id>]', () => {
    const html =
      'Anterior was faster <sup data-citation="true" data-article-id="abc">[1]</sup>.'
    expect(htmlToAiSafeText(html)).toBe('Anterior was faster [CITE_abc].')
  })

  it('handles attribute order variation', () => {
    const html =
      'X <sup data-article-id="xyz" data-citation>[2]</sup> Y'
    expect(htmlToAiSafeText(html)).toBe('X [CITE_xyz] Y')
  })

  it('returns empty string for empty input', () => {
    expect(htmlToAiSafeText('')).toBe('')
  })

  it('preserves non-citation HTML untouched', () => {
    const html = 'Some <strong>bold</strong> text.'
    expect(htmlToAiSafeText(html)).toBe('Some <strong>bold</strong> text.')
  })
})

describe('aiSafeTextToHtml', () => {
  it('converts known [CITE_<id>] back to <sup> markers', () => {
    const text = 'Anterior was faster [CITE_abc].'
    const out = aiSafeTextToHtml(text, new Set(['abc']))
    expect(out).toContain('<sup')
    expect(out).toContain('data-article-id="abc"')
  })

  it('leaves unknown CITE tokens as literal text (hallucination signal)', () => {
    const text = 'Real [CITE_abc] and fake [CITE_xyz].'
    const out = aiSafeTextToHtml(text, new Set(['abc']))
    expect(out).toContain('data-article-id="abc"')
    expect(out).toContain('[CITE_xyz]')
  })

  it('round-trips through htmlToAiSafeText', () => {
    const original = 'X <sup data-citation="true" data-article-id="abc">[1]</sup> Y'
    const safe = htmlToAiSafeText(original)
    const back = aiSafeTextToHtml(safe, new Set(['abc']))
    expect(back).toContain('data-article-id="abc"')
    expect(back).toContain('Y')
    expect(back).toContain('X')
  })
})
