/**
 * Citation numbering engine.
 *
 * Walks a TipTap doc (or HTML string) and assigns 1-based Vancouver-style numbers
 * to each unique `articleId` in order of first appearance. The same `articleId`
 * gets the same number wherever it appears.
 */

export type CitationNumberMap = Map<string, number>

/** Build a numbering map from a TipTap JSON doc. */
export function numberCitationsFromDoc(doc: unknown): CitationNumberMap {
  const map: CitationNumberMap = new Map()
  let next = 1
  walk(doc, (node) => {
    if (
      node &&
      typeof node === 'object' &&
      'type' in node &&
      (node as { type: string }).type === 'citation'
    ) {
      const attrs = (node as { attrs?: { articleId?: string } }).attrs
      const id = attrs?.articleId
      if (id && !map.has(id)) {
        map.set(id, next++)
      }
    }
  })
  return map
}

/** Build a numbering map from raw HTML by walking <sup data-citation> elements. */
export function numberCitationsFromHtml(html: string): CitationNumberMap {
  const map: CitationNumberMap = new Map()
  let next = 1
  if (!html) return map
  const parser = new DOMParser()
  const doc = parser.parseFromString(`<div>${html}</div>`, 'text/html')
  doc.querySelectorAll('sup[data-citation]').forEach((el) => {
    const id = el.getAttribute('data-article-id')
    if (id && !map.has(id)) map.set(id, next++)
  })
  return map
}

/** Build a numbering map across multiple HTML strings (for Final Manuscript). */
export function numberCitationsAcross(htmlSections: string[]): CitationNumberMap {
  const map: CitationNumberMap = new Map()
  let next = 1
  for (const html of htmlSections) {
    if (!html) continue
    const parser = new DOMParser()
    const doc = parser.parseFromString(`<div>${html}</div>`, 'text/html')
    doc.querySelectorAll('sup[data-citation]').forEach((el) => {
      const id = el.getAttribute('data-article-id')
      if (id && !map.has(id)) map.set(id, next++)
    })
  }
  return map
}

function walk(node: unknown, fn: (n: unknown) => void): void {
  if (!node || typeof node !== 'object') return
  fn(node)
  const content = (node as { content?: unknown[] }).content
  if (Array.isArray(content)) {
    for (const child of content) walk(child, fn)
  }
}
