/**
 * Phase D4.1 — Manuscript offset mapping.
 *
 * The existing comments backend (``/api/projects/{id}/comments``) anchors
 * each comment to a manuscript section by ``section_name`` plus a pair
 * of character offsets (``anchor_start`` / ``anchor_end``) measured into
 * the section's *plain text*. The mobile manuscript reader, however,
 * speaks in paragraphs (``data-paragraph-id="<Section>-p<N>"``) and
 * word indices (a long-press picks a word, drag handles extend the
 * range word-by-word). This helper bridges the two:
 *
 *   1. ``paragraphOffsets(sectionText)`` — given a section's *raw HTML*
 *      (the canonical shape the manuscript backend serves), split it
 *      into paragraph fragments and return ``{ paragraphId, start, end }``
 *      tuples where ``start``/``end`` are plain-text character offsets
 *      into the section's full plain-text body.
 *
 *   2. ``wordRangeToOffsets(paragraphHtml, wordStart, wordEnd)`` — given
 *      a paragraph and a pair of word indices (closed-interval, M2-style),
 *      return the character offsets *within the paragraph's plain text*.
 *      Combine with ``paragraphOffsets`` to obtain section-level offsets.
 *
 *   3. ``offsetsToHighlightSpans(comments, sectionHtml)`` — given a list
 *      of existing comments + the section HTML, render a paragraph-keyed
 *      array of ``RenderSpan``s that the UI walks to interleave plain
 *      text + ``<sup>`` chips + ``<mark data-comment-id>`` wrappers.
 *      Overlapping comments are split into nested spans (each character
 *      tracks the set of comment IDs that cover it; we emit one span per
 *      transition).
 *
 *   4. ``htmlPlainTextMap(html)`` — walk the section's HTML once and
 *      build a list of ``{ htmlIndex, plainIndex }`` cut-points. The
 *      mapping is monotonic and lets the renderer translate a plain-text
 *      offset back to a position in the HTML stream so we can splice
 *      ``<mark>`` wrappers in *without* destroying inline ``<sup
 *      data-citation>`` chips. This is the key D4.4 invariant: comment
 *      offsets must not shift when a citation is inserted or removed.
 *
 * Everything in this module is pure and DOM-free — it runs identically
 * under jsdom and Node, so the tests stay fast.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ParagraphOffset = {
  /** Stable ID of the form ``p<N>`` — N is the paragraph index. */
  paragraphId: string
  /** Inclusive plain-text start offset within the section. */
  start: number
  /** Exclusive plain-text end offset within the section. */
  end: number
  /** The raw HTML fragment for this paragraph (e.g. ``<p>...</p>``). */
  html: string
  /** The plain text of this paragraph (citation chip text inlined). */
  text: string
}

export type CommentLike = {
  id: string
  section_name: string
  anchor_start: number
  anchor_end: number
  body?: string
  colour?: string | null
}

/**
 * One element of the render plan for a paragraph. Each span carries the
 * raw HTML to emit + the set of comment IDs (if any) that cover it. The
 * UI wraps any span with ``commentIds.length > 0`` in a
 * ``<mark data-comment-id>`` (or comma-joined IDs for overlaps).
 */
export type RenderSpan = {
  /** HTML fragment to render verbatim (includes inline ``<sup>`` chips). */
  html: string
  /** Comment IDs that cover this span, in stable creation order. */
  commentIds: string[]
}

export type ParagraphRenderPlan = {
  paragraphId: string
  /** The unchanged ``<p ...>`` opening tag. */
  openTag: string
  /** The unchanged ``</p>`` closing tag (always ``</p>``). */
  closeTag: string
  /** Ordered list of spans that, joined, reproduce the inner HTML. */
  spans: RenderSpan[]
}

// ---------------------------------------------------------------------------
// Internals — paragraph splitting
// ---------------------------------------------------------------------------

const P_TAG_RE = /^<p\b([^>]*)>([\s\S]*)<\/p>$/i

function splitParagraphsHtml(sectionHtml: string): string[] {
  if (!sectionHtml || !sectionHtml.trim()) return []
  const parts = sectionHtml.split(/(?<=<\/p>)/i)
  return parts.map((p) => p.trim()).filter((p) => p.length > 0)
}

// ---------------------------------------------------------------------------
// htmlPlainTextMap — the core HTML↔plain-text bridge
// ---------------------------------------------------------------------------

/**
 * One cut-point in the mapping between the source HTML stream and the
 * derived plain-text stream. Both indices are monotonically increasing.
 *
 * Anatomy of a cut-point: if ``htmlIndex = 12`` and ``plainIndex = 5``,
 * the character at HTML offset 12 is the same logical character as
 * plain offset 5. We emit a cut-point at the *start* of every text
 * chunk and at the *start* of every tag.
 */
export type HtmlPlainCut = {
  htmlIndex: number
  plainIndex: number
}

export type HtmlPlainMap = {
  /** Reconstructed plain text. */
  plain: string
  /** Ordered cut-points. The last entry's htmlIndex == html.length. */
  cuts: HtmlPlainCut[]
}

/**
 * Walk through ``html`` and produce a plain-text version + a mapping
 * back to the original HTML offsets.
 *
 * Rules:
 *   - Tags (``<...>``) contribute zero plain-text characters, but their
 *     *inner text* does. ``<sup data-citation>1</sup>`` produces the
 *     plain character ``1``.
 *   - HTML entities ``&amp;`` / ``&lt;`` / ``&gt;`` / ``&nbsp;`` /
 *     ``&quot;`` / ``&#NN;`` are decoded to a single plain character.
 *   - Block boundaries are NOT special — callers handle paragraph
 *     boundaries separately. We keep the mapping ASCII-flat.
 */
export function htmlPlainTextMap(html: string): HtmlPlainMap {
  const cuts: HtmlPlainCut[] = []
  let plain = ''
  let i = 0
  let lastHtmlIndex = -1
  let lastPlainIndex = -1

  function pushCut(h: number, p: number) {
    if (h === lastHtmlIndex && p === lastPlainIndex) return
    cuts.push({ htmlIndex: h, plainIndex: p })
    lastHtmlIndex = h
    lastPlainIndex = p
  }

  while (i < html.length) {
    const ch = html[i]
    if (ch === '<') {
      // Skip the entire tag. No plain-text contribution, but record a
      // cut so callers can map "just before <tag>" → current plain idx.
      pushCut(i, plain.length)
      const end = html.indexOf('>', i)
      if (end === -1) {
        // Malformed — bail and treat the rest as opaque text.
        break
      }
      i = end + 1
      pushCut(i, plain.length)
      continue
    }
    if (ch === '&') {
      // HTML entity. Decode to a single character and record one cut.
      const end = html.indexOf(';', i)
      if (end !== -1 && end - i <= 8) {
        const entity = html.slice(i, end + 1)
        const decoded = decodeEntity(entity)
        if (decoded !== null) {
          pushCut(i, plain.length)
          plain += decoded
          i = end + 1
          continue
        }
      }
      // Unknown entity — treat as literal.
      pushCut(i, plain.length)
      plain += ch
      i += 1
      continue
    }
    // Plain character.
    pushCut(i, plain.length)
    plain += ch
    i += 1
  }
  // Final cut at end.
  pushCut(html.length, plain.length)
  return { plain, cuts }
}

function decodeEntity(entity: string): string | null {
  switch (entity) {
    case '&amp;':
      return '&'
    case '&lt;':
      return '<'
    case '&gt;':
      return '>'
    case '&quot;':
      return '"'
    case '&apos;':
      return "'"
    case '&nbsp;':
      return ' '
  }
  if (entity.startsWith('&#')) {
    const inner = entity.slice(2, -1)
    if (inner.startsWith('x') || inner.startsWith('X')) {
      const n = parseInt(inner.slice(1), 16)
      if (Number.isFinite(n)) return String.fromCodePoint(n)
    } else {
      const n = parseInt(inner, 10)
      if (Number.isFinite(n)) return String.fromCodePoint(n)
    }
  }
  return null
}

/**
 * Translate a plain-text offset into the corresponding HTML offset for
 * the source string the map was built from. Offsets that fall between
 * two cut-points are linearly interpolated (which is safe because every
 * plain character corresponds to exactly one HTML character or one
 * entity run, and entities never overlap).
 */
export function plainOffsetToHtmlOffset(
  map: HtmlPlainMap,
  plainOffset: number,
): number {
  if (plainOffset <= 0) return map.cuts[0]?.htmlIndex ?? 0
  if (plainOffset >= map.plain.length) {
    return map.cuts[map.cuts.length - 1]?.htmlIndex ?? 0
  }
  // Binary-search the cut whose plainIndex <= plainOffset.
  let lo = 0
  let hi = map.cuts.length - 1
  while (lo < hi) {
    const mid = (lo + hi + 1) >>> 1
    if (map.cuts[mid].plainIndex <= plainOffset) lo = mid
    else hi = mid - 1
  }
  const cut = map.cuts[lo]
  const delta = plainOffset - cut.plainIndex
  return cut.htmlIndex + delta
}

// ---------------------------------------------------------------------------
// paragraphOffsets
// ---------------------------------------------------------------------------

/**
 * Compute per-paragraph offsets within the *plain text* of a section.
 *
 * The section's plain text is the concatenation of each paragraph's
 * plain text joined by a single ``\n`` — this matches the convention
 * the desktop reader uses when displaying section-wide character
 * counts. The newline is included in the cumulative offset so the
 * next paragraph's ``start`` is consistent.
 */
export function paragraphOffsets(sectionHtml: string): ParagraphOffset[] {
  const parts = splitParagraphsHtml(sectionHtml)
  const out: ParagraphOffset[] = []
  let cursor = 0
  for (let i = 0; i < parts.length; i++) {
    const html = parts[i]
    const inner = extractInnerHtml(html)
    const map = htmlPlainTextMap(inner)
    const text = map.plain
    const start = cursor
    const end = cursor + text.length
    out.push({
      paragraphId: `p${i}`,
      start,
      end,
      html,
      text,
    })
    // +1 for the synthetic newline separator between paragraphs (but
    // not after the final paragraph — keeps lengths tidy).
    cursor = end + (i < parts.length - 1 ? 1 : 0)
  }
  return out
}

function extractInnerHtml(paragraphHtml: string): string {
  const m = P_TAG_RE.exec(paragraphHtml)
  return m ? m[2] : paragraphHtml
}

function extractOpenTag(paragraphHtml: string): string {
  const m = P_TAG_RE.exec(paragraphHtml)
  if (!m) return '<p>'
  const attrs = m[1] ?? ''
  return `<p${attrs}>`
}

// ---------------------------------------------------------------------------
// wordRangeToOffsets
// ---------------------------------------------------------------------------

/**
 * Given a paragraph (raw HTML), a word-index range (closed interval),
 * and the paragraph's *base offset* within the section's plain text,
 * return the section-level character offsets that cover the selected
 * words.
 *
 * Word splitting matches ``segmentText`` in ``MobileReader`` — words
 * are runs of non-whitespace separated by ``\s+``. We perform the split
 * against the paragraph's plain text (so citation chips count as a
 * single word, e.g. ``[1]``).
 */
export function wordRangeToOffsets(
  paragraphHtml: string,
  wordStart: number,
  wordEnd: number,
  paragraphBaseOffset = 0,
): { anchor_start: number; anchor_end: number } {
  const inner = extractInnerHtml(paragraphHtml)
  const map = htmlPlainTextMap(inner)
  const plain = map.plain
  // Walk plain text, collect (start, end) for each word.
  const words: { s: number; e: number }[] = []
  let i = 0
  while (i < plain.length) {
    // Skip whitespace.
    while (i < plain.length && /\s/.test(plain[i])) i++
    if (i >= plain.length) break
    const s = i
    while (i < plain.length && !/\s/.test(plain[i])) i++
    words.push({ s, e: i })
  }
  if (words.length === 0) {
    return {
      anchor_start: paragraphBaseOffset,
      anchor_end: paragraphBaseOffset,
    }
  }
  const lo = clamp(Math.min(wordStart, wordEnd), 0, words.length - 1)
  const hi = clamp(Math.max(wordStart, wordEnd), 0, words.length - 1)
  return {
    anchor_start: paragraphBaseOffset + words[lo].s,
    anchor_end: paragraphBaseOffset + words[hi].e,
  }
}

function clamp(n: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, n))
}

// ---------------------------------------------------------------------------
// offsetsToHighlightSpans
// ---------------------------------------------------------------------------

/**
 * Per-paragraph render plan: walks each paragraph, intersects each
 * comment's [anchor_start, anchor_end) range with the paragraph's
 * [start, end) range, and emits a sequence of ``RenderSpan``s. The
 * spans, when joined, reconstruct the paragraph's original inner HTML
 * (so inline ``<sup data-citation>`` chips, ``<strong>``, etc. are all
 * preserved). Spans covered by ≥1 comment receive ``commentIds`` for
 * the renderer to wrap in ``<mark data-comment-id>``.
 */
export function offsetsToHighlightSpans(
  comments: CommentLike[],
  sectionHtml: string,
): ParagraphRenderPlan[] {
  const paragraphs = paragraphOffsets(sectionHtml)
  return paragraphs.map((p) => {
    const inner = extractInnerHtml(p.html)
    const openTag = extractOpenTag(p.html)
    const closeTag = '</p>'
    const map = htmlPlainTextMap(inner)

    // 1. Project each comment into paragraph-local plain-text range.
    type Hit = { id: string; lo: number; hi: number }
    const hits: Hit[] = []
    for (const c of comments) {
      const lo = Math.max(c.anchor_start, p.start) - p.start
      const hi = Math.min(c.anchor_end, p.end) - p.start
      if (hi > lo) hits.push({ id: c.id, lo, hi })
    }
    if (hits.length === 0) {
      return {
        paragraphId: p.paragraphId,
        openTag,
        closeTag,
        spans: [{ html: inner, commentIds: [] }],
      }
    }

    // 2. Build the set of cut-points: every hit boundary + paragraph
    //    boundaries. Sorted unique, in plain-text coordinates.
    const cutSet = new Set<number>([0, map.plain.length])
    for (const h of hits) {
      cutSet.add(clamp(h.lo, 0, map.plain.length))
      cutSet.add(clamp(h.hi, 0, map.plain.length))
    }
    const cutList = Array.from(cutSet).sort((a, b) => a - b)

    // 3. Emit spans between consecutive cut-points. For each, compute
    //    which comment IDs cover the *midpoint* (sufficient since
    //    cut-points include every boundary).
    const spans: RenderSpan[] = []
    for (let k = 0; k < cutList.length - 1; k++) {
      const plainStart = cutList[k]
      const plainEnd = cutList[k + 1]
      if (plainEnd <= plainStart) continue
      const htmlStart = plainOffsetToHtmlOffset(map, plainStart)
      const htmlEnd = plainOffsetToHtmlOffset(map, plainEnd)
      // Extend htmlEnd through any trailing close tags so we don't
      // emit an unbalanced span like ``<sup data-citation>1`` without
      // its closing ``</sup>``. We only sweep forward through *closing*
      // tags, which are zero-width in plain-text terms.
      let extEnd = htmlEnd
      if (k === cutList.length - 2) extEnd = inner.length
      const html = inner.slice(htmlStart, extEnd)
      if (!html) continue
      const mid = (plainStart + plainEnd) / 2
      const ids = hits.filter((h) => h.lo <= mid && mid < h.hi).map((h) => h.id)
      spans.push({ html, commentIds: ids })
    }

    return {
      paragraphId: p.paragraphId,
      openTag,
      closeTag,
      spans,
    }
  })
}

// ---------------------------------------------------------------------------
// Convenience: locate the paragraph that owns a paragraphId.
// ---------------------------------------------------------------------------

export function findParagraphById(
  sectionHtml: string,
  paragraphId: string,
): ParagraphOffset | null {
  const all = paragraphOffsets(sectionHtml)
  return all.find((p) => p.paragraphId === paragraphId) ?? null
}
