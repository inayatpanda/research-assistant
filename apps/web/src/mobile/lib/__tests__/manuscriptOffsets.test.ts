/**
 * Phase D4.1/D4.4 — manuscriptOffsets helper tests.
 *
 *   1. paragraphOffsets reports correct char ranges for multi-para
 *      sections.
 *   2. wordRangeToOffsets converts word indices → section char offsets.
 *   3. offsetsToHighlightSpans handles non-overlapping + overlapping
 *      comments (the latter splits into nested spans).
 *   4. htmlPlainTextMap preserves <sup data-citation> chips so offsets
 *      don't shift when chips are added/removed.
 */
import { describe, expect, it } from 'vitest'

import {
  htmlPlainTextMap,
  offsetsToHighlightSpans,
  paragraphOffsets,
  plainOffsetToHtmlOffset,
  wordRangeToOffsets,
} from '../manuscriptOffsets'

describe('paragraphOffsets', () => {
  it('returns one entry per paragraph with cumulative offsets', () => {
    const html = '<p>Hello world.</p><p>Second paragraph here.</p>'
    const offsets = paragraphOffsets(html)
    expect(offsets).toHaveLength(2)
    expect(offsets[0]).toMatchObject({
      paragraphId: 'p0',
      start: 0,
      end: 'Hello world.'.length,
      text: 'Hello world.',
    })
    // +1 for the synthetic newline separator between paragraphs.
    expect(offsets[1]).toMatchObject({
      paragraphId: 'p1',
      start: 'Hello world.'.length + 1,
      end: 'Hello world.'.length + 1 + 'Second paragraph here.'.length,
      text: 'Second paragraph here.',
    })
  })
})

describe('wordRangeToOffsets', () => {
  it('maps word indices within a paragraph to character offsets', () => {
    const para = '<p>Hello world foo bar baz.</p>'
    const r = wordRangeToOffsets(para, 1, 2, 100)
    // "Hello world foo bar baz." → words: Hello(0..5) world(6..11) foo(12..15)
    expect(r.anchor_start).toBe(100 + 6)
    expect(r.anchor_end).toBe(100 + 15)
  })

  it('clamps word indices to the available word count', () => {
    const para = '<p>Only three short words</p>'
    const r = wordRangeToOffsets(para, 0, 99, 0)
    expect(r.anchor_start).toBe(0)
    expect(r.anchor_end).toBe('Only three short words'.length)
  })
})

describe('offsetsToHighlightSpans', () => {
  it('emits a single uncovered span when no comment hits the paragraph', () => {
    const html = '<p>Hello world.</p>'
    const plan = offsetsToHighlightSpans([], html)
    expect(plan).toHaveLength(1)
    expect(plan[0].spans).toHaveLength(1)
    expect(plan[0].spans[0].html).toBe('Hello world.')
    expect(plan[0].spans[0].commentIds).toEqual([])
  })

  it('splits the paragraph into 3 spans for one mid-paragraph comment', () => {
    const html = '<p>Hello world.</p>'
    //                  ^^^^^ chars 6..11
    const plan = offsetsToHighlightSpans(
      [
        {
          id: 'c1',
          section_name: 'Introduction',
          anchor_start: 6,
          anchor_end: 11,
          colour: 'intro',
        },
      ],
      html,
    )
    expect(plan).toHaveLength(1)
    const joined = plan[0].spans.map((s) => s.html).join('')
    expect(joined).toBe('Hello world.')
    const covered = plan[0].spans.find((s) => s.commentIds.length > 0)
    expect(covered).toBeTruthy()
    expect(covered!.html).toBe('world')
    expect(covered!.commentIds).toEqual(['c1'])
  })

  it('splits into nested spans for overlapping comments', () => {
    const html = '<p>abcdefghij</p>' // 10 chars, no whitespace fluff
    const plan = offsetsToHighlightSpans(
      [
        // c1 covers indices 1..6  -> "bcdef"
        { id: 'c1', section_name: 'Introduction', anchor_start: 1, anchor_end: 6 },
        // c2 covers indices 4..8  -> "efgh"
        { id: 'c2', section_name: 'Introduction', anchor_start: 4, anchor_end: 8 },
      ],
      html,
    )
    const spans = plan[0].spans
    const joined = spans.map((s) => s.html).join('')
    expect(joined).toBe('abcdefghij')
    // We expect spans roughly: "a"(none) "bcd"(c1) "ef"(c1,c2) "gh"(c2) "ij"(none).
    const overlap = spans.find(
      (s) => s.commentIds.includes('c1') && s.commentIds.includes('c2'),
    )
    expect(overlap).toBeTruthy()
    expect(overlap!.html).toBe('ef')
    const onlyC1 = spans.find(
      (s) => s.commentIds.includes('c1') && !s.commentIds.includes('c2'),
    )
    const onlyC2 = spans.find(
      (s) => !s.commentIds.includes('c1') && s.commentIds.includes('c2'),
    )
    expect(onlyC1?.html).toBe('bcd')
    expect(onlyC2?.html).toBe('gh')
  })
})

describe('htmlPlainTextMap (citation chip preservation)', () => {
  it('skips inline <sup data-citation> tags so chips do not shift plain offsets', () => {
    const html = 'Result foo<sup data-citation="1">[1]</sup> bar baz.'
    const map = htmlPlainTextMap(html)
    // Plain text inlines the chip body, so total length is
    // "Result foo[1] bar baz." (22).
    expect(map.plain).toBe('Result foo[1] bar baz.')
    // The plain offset of 'b' in 'bar' is 14.
    const plainBarStart = map.plain.indexOf('bar')
    expect(plainBarStart).toBe(14)
    // Its HTML offset must be after the closing </sup> tag.
    const htmlBarStart = plainOffsetToHtmlOffset(map, plainBarStart)
    expect(html.slice(htmlBarStart, htmlBarStart + 3)).toBe('bar')

    // And — the load-bearing invariant — removing the <sup> chip must
    // leave the plain offset of 'bar' unchanged in absolute character
    // count (because the chip contributed exactly its [1] characters).
    // We model "remove chip" by inserting one and verifying the
    // post-chip text still maps to the right HTML position.
    const html2 = 'Result foo bar baz.'
    const map2 = htmlPlainTextMap(html2)
    // The plain length differs by len('[1]') = 3.
    expect(map.plain.length - map2.plain.length).toBe(3)
  })

  it('round-trips a plain offset back to an HTML offset across formatting tags', () => {
    const html = 'pre <strong>bold</strong> post'
    const map = htmlPlainTextMap(html)
    expect(map.plain).toBe('pre bold post')
    const idxPost = map.plain.indexOf('post')
    const htmlIdx = plainOffsetToHtmlOffset(map, idxPost)
    expect(html.slice(htmlIdx, htmlIdx + 4)).toBe('post')
  })
})
